#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
TABLE_NAME = "url_shortener_links"
ROLE_NAME = "EC2-URLShortener-Role"
POLICY_NAME = "URLShortenerDynamoDBPolicy"
SG_NAME = "url-shortener-sg"
KEY_NAME = "url-shortener-key"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

session = boto3.Session(region_name=REGION)
sts = session.client("sts")
account_id = sts.get_caller_identity()["Account"]
print(f"[OK] Sesion AWS iniciada para la cuenta: {account_id} en region: {REGION}")

# ==========================================
# 1. DynamoDB
# ==========================================
print("\n--- 1. Configurando Amazon DynamoDB ---")
dynamodb_res = session.resource("dynamodb")
dynamodb_cli = session.client("dynamodb")

try:
    table = dynamodb_res.Table(TABLE_NAME)
    table.load()
    print(f"[INFO] La tabla DynamoDB '{TABLE_NAME}' ya existe (Estado: {table.table_status}).")
except ClientError as e:
    if e.response["Error"]["Code"] == "ResourceNotFoundException":
        print(f"[ACCION] Creando tabla DynamoDB '{TABLE_NAME}'...")
        table = dynamodb_res.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "short_code", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "short_code", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        print("Esperando a que la tabla este activa...")
        table.wait_until_exists()
        print(f"[OK] Tabla '{TABLE_NAME}' creada y activa.")
    else:
        raise e

# ==========================================
# 2. IAM Policy, Role e Instance Profile
# ==========================================
print("\n--- 2. Configurando Rol IAM para EC2 ---")
iam = session.client("iam")

policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBTableAccess",
            "Effect": "Allow",
            "Action": ["dynamodb:PutItem", "dynamodb:GetItem"],
            "Resource": f"arn:aws:dynamodb:{REGION}:{account_id}:table/{TABLE_NAME}"
        }
    ]
}

policy_arn = f"arn:aws:iam::{account_id}:policy/{POLICY_NAME}"
try:
    resp = iam.create_policy(
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(policy_document),
        Description="Acceso minimo necesario a DynamoDB para URL Shortener"
    )
    policy_arn = resp["Policy"]["Arn"]
    print(f"[OK] Politica IAM creada: {policy_arn}")
except ClientError as e:
    if e.response["Error"]["Code"] == "EntityAlreadyExists":
        print(f"[INFO] Politica IAM '{POLICY_NAME}' ya existe: {policy_arn}")
    else:
        raise e

assume_role_doc = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

try:
    iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(assume_role_doc),
        Description="Rol para instancia EC2 del URL Shortener con acceso a DynamoDB"
    )
    print(f"[OK] Rol IAM creado: {ROLE_NAME}")
except ClientError as e:
    if e.response["Error"]["Code"] == "EntityAlreadyExists":
        print(f"[INFO] Rol IAM '{ROLE_NAME}' ya existe.")
    else:
        raise e

iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy_arn)
print(f"[OK] Politica adjuntada al rol '{ROLE_NAME}'.")

try:
    iam.create_instance_profile(InstanceProfileName=ROLE_NAME)
    print(f"[OK] Instance Profile creado: {ROLE_NAME}")
except ClientError as e:
    if e.response["Error"]["Code"] == "EntityAlreadyExists":
        print(f"[INFO] Instance Profile '{ROLE_NAME}' ya existe.")
    else:
        raise e

try:
    iam.add_role_to_instance_profile(
        InstanceProfileName=ROLE_NAME,
        RoleName=ROLE_NAME
    )
    print(f"[OK] Rol agregado al Instance Profile.")
except ClientError as e:
    if e.response["Error"]["Code"] == "LimitExceeded":
        pass
    else:
        print(f"[INFO] Rol ya estaba en Instance Profile.")

print("Esperando 10 segundos para propagacion de permisos IAM...")
time.sleep(10)

# ==========================================
# 3. Security Group y Key Pair en EC2
# ==========================================
print("\n--- 3. Configurando Red y Seguridad en Amazon EC2 ---")
ec2_cli = session.client("ec2")
ec2_res = session.resource("ec2")

vpcs = ec2_cli.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"]
if not vpcs:
    vpcs = ec2_cli.describe_vpcs()["Vpcs"]
vpc_id = vpcs[0]["VpcId"]
print(f"[INFO] Utilizando VPC: {vpc_id}")

try:
    sg_resp = ec2_cli.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [SG_NAME]}, {"Name": "vpc-id", "Values": [vpc_id]}]
    )
    if sg_resp["SecurityGroups"]:
        sg_id = sg_resp["SecurityGroups"][0]["GroupId"]
        print(f"[INFO] Security Group '{SG_NAME}' ya existe: {sg_id}")
    else:
        raise ClientError({"Error": {"Code": "InvalidGroup.NotFound"}}, "describe_security_groups")
except ClientError:
    print(f"[ACCION] Creando Security Group '{SG_NAME}'...")
    sg = ec2_cli.create_security_group(
        GroupName=SG_NAME,
        Description="Permite trafico SSH (22) y FastAPI (8000) para URL Shortener",
        VpcId=vpc_id
    )
    sg_id = sg["GroupId"]
    print(f"[OK] Security Group creado: {sg_id}")

    ec2_cli.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "SSH"}]
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 8000,
                "ToPort": 8000,
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "FastAPI HTTP"}]
            }
        ]
    )
    print("[OK] Reglas de entrada SSH (22) y FastAPI (8000) autorizadas.")

key_path = PROJECT_ROOT / f"{KEY_NAME}.pem"
try:
    ec2_cli.describe_key_pairs(KeyNames=[KEY_NAME])
    print(f"[INFO] Key Pair '{KEY_NAME}' ya existe en AWS.")
except ClientError:
    print(f"[ACCION] Creando Key Pair '{KEY_NAME}'...")
    key_resp = ec2_cli.create_key_pair(KeyName=KEY_NAME)
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(key_resp["KeyMaterial"])
    print(f"[OK] Key Pair creado y guardado en: {key_path}")

# ==========================================
# 4. AMI y Lanzamiento de Instancia EC2
# ==========================================
print("\n--- 4. Lanzando Instancia EC2 con Despliegue Automatico ---")
ssm = session.client("ssm")
try:
    ami_param = ssm.get_parameter(Name="/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id")
    ami_id = ami_param["Parameter"]["Value"]
    print(f"[INFO] AMI seleccionada (Ubuntu 24.04 LTS via SSM): {ami_id}")
except Exception:
    ami_id = "ami-0e2c8caa4b6378d8c"
    print(f"[INFO] Usando AMI por defecto: {ami_id}")

user_data_script = f"""#!/bin/bash
set -e
exec > /var/log/user-data.log 2>&1
echo "=== INICIANDO DESPLIEGUE AUTOMATICO DE FASTAPI ==="

apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl

# Obtener IP publica
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60" || true)
PUBLIC_IP=""
if [ -n "$TOKEN" ]; then
    PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 || true)
fi
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s https://checkip.amazonaws.com || true)
fi

echo "IP detectada: $PUBLIC_IP"

# Clonar repo
cd /home/ubuntu
git clone https://github.com/A-Krycek/10.-Midterm---Practical.git aws-url-shortener
chown -R ubuntu:ubuntu /home/ubuntu/aws-url-shortener

cd /home/ubuntu/aws-url-shortener/backend
sudo -u ubuntu python3 -m venv venv
sudo -u ubuntu ./venv/bin/pip install --upgrade pip
sudo -u ubuntu ./venv/bin/pip install -r requirements.txt

# Generar archivo .env
cat <<EOF > /home/ubuntu/aws-url-shortener/backend/.env
AWS_REGION={REGION}
DYNAMODB_TABLE_NAME={TABLE_NAME}
BASE_URL=http://${{PUBLIC_IP}}:8000
CORS_ORIGINS=*
EOF
chown ubuntu:ubuntu /home/ubuntu/aws-url-shortener/backend/.env

# Configurar e iniciar systemd
cat <<EOF > /etc/systemd/system/urlshortener.service
[Unit]
Description=FastAPI URL Shortener Service (EC2)
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/aws-url-shortener/backend
EnvironmentFile=/home/ubuntu/aws-url-shortener/backend/.env
ExecStart=/home/ubuntu/aws-url-shortener/backend/venv/bin/fastapi run app/main.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable urlshortener
systemctl start urlshortener
echo "=== DESPLIEGUE FINALIZADO CON EXITO ==="
"""

# Comprobar si ya hay una instancia corriendo con ese nombre
existing_instances = ec2_cli.describe_instances(
    Filters=[
        {"Name": "tag:Name", "Values": ["URL-Shortener-Backend"]},
        {"Name": "instance-state-name", "Values": ["pending", "running"]}
    ]
)["Reservations"]

instance_id = None
public_ip = None

if existing_instances:
    inst = existing_instances[0]["Instances"][0]
    instance_id = inst["InstanceId"]
    public_ip = inst.get("PublicIpAddress")
    print(f"[INFO] Instancia EC2 existente encontrada: {instance_id} (IP: {public_ip})")
else:
    print("[ACCION] Lanzando nueva instancia EC2 'URL-Shortener-Backend' (t3.micro)...")
    launch_resp = ec2_cli.run_instances(
        ImageId=ami_id,
        InstanceType="t3.micro",
        KeyName=KEY_NAME,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={"Name": ROLE_NAME},
        MinCount=1,
        MaxCount=1,
        UserData=user_data_script,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": "URL-Shortener-Backend"}]
            }
        ]
    )
    instance_id = launch_resp["Instances"][0]["InstanceId"]
    print(f"[OK] Instancia creada con ID: {instance_id}")

print("Esperando a que la instancia EC2 este en estado 'running'...")
waiter = ec2_cli.get_waiter("instance_running")
waiter.wait(InstanceIds=[instance_id])

inst_desc = ec2_cli.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
public_ip = inst_desc["PublicIpAddress"]
print(f"[OK] Instancia EC2 activa. Direccion IP Publica: {public_ip}")
print(f"     Endpoint de la API: http://{public_ip}:8000")

# ==========================================
# 5. Amazon S3 (Frontend Estatico)
# ==========================================
print("\n--- 5. Desplegando Frontend en Amazon S3 ---")
s3 = session.client("s3")
bucket_name = f"url-shortener-krycek-{account_id}"

try:
    if REGION == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": REGION}
        )
    print(f"[OK] Bucket S3 creado: {bucket_name}")
except ClientError as e:
    if e.response["Error"]["Code"] in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
        print(f"[INFO] Bucket S3 '{bucket_name}' ya existe.")
    else:
        raise e

# Desactivar bloqueo de acceso publico
s3.put_public_access_block(
    Bucket=bucket_name,
    PublicAccessBlockConfiguration={
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False
    }
)
print("[OK] Acceso publico habilitado para el bucket S3.")

# Configurar Static Website Hosting
s3.put_bucket_website(
    Bucket=bucket_name,
    WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}}
)
print("[OK] Static Website Hosting habilitado.")

# Politica de lectura publica
s3_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
        }
    ]
}
s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(s3_policy))
print("[OK] Politica publica de lectura aplicada al bucket.")

# Actualizar config.js local con la IP publica de EC2
frontend_dir = PROJECT_ROOT / "frontend"
config_js_content = f"""// Configuracion generada automaticamente para produccion
const APP_CONFIG = {{
  API_BASE_URL: "http://{public_ip}:8000"
}};
"""
with open(frontend_dir / "config.js", "w", encoding="utf-8") as f:
    f.write(config_js_content)

# Subir archivos estaticos a S3
content_types = {
    "index.html": "text/html",
    "styles.css": "text/css",
    "app.js": "application/javascript",
    "config.js": "application/javascript"
}

for filename, ctype in content_types.items():
    file_path = frontend_dir / filename
    with open(file_path, "rb") as f:
        s3.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=f.read(),
            ContentType=ctype
        )
    print(f"[OK] Subido a S3: {filename} ({ctype})")

s3_website_url = f"http://{bucket_name}.s3-website-{REGION}.amazonaws.com"

print("\n" + "=" * 65)
print("     ¡DESPLIEGUE EN AWS COMPLETADO CON EXITO!")
print("=" * 65)
print(f"1. Frontend en Amazon S3:   {s3_website_url}")
print(f"2. Backend en Amazon EC2:   http://{public_ip}:8000")
print(f"3. Documentacion Swagger:  http://{public_ip}:8000/docs")
print(f"4. Tabla DynamoDB:          {TABLE_NAME}")
print(f"5. Llave SSH guardada en:   {key_path}")
print("=" * 65)
print("Nota: EC2 tarda aproximadamente 1 a 2 minutos en completar")
print("la instalacion inicial y levantar FastAPI con systemd.")
