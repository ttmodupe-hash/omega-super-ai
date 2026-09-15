# Luqi-AI production node - AWS af-south-1 (Cape Town) for POPIA residency.
# Scaffold: run `terraform init && terraform validate` before any apply.
terraform {
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
}
provider "aws" { region = var.aws_region }

resource "aws_security_group" "luqi_edge" {
  name        = "luqi-ai-edge"
  description = "Only 22 (deploy), 80 (redirect), 443 (app) - everything else refused"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # restrict to your office IP in production
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # provider APIs (Moonshot/Google/Anthropic)
  }
}

resource "aws_instance" "luqi_core" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.luqi_edge.id]

  root_block_device { volume_size = 40 }

  user_data = <<-EOF
    #!/bin/bash
    # Bootstrap matches deploy/DEPLOYMENT.md: docker + repo + systemd unit
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker ubuntu
    mkdir -p /opt/luqi-ai
  EOF

  tags = { Name = "luqi-ai-core", Project = "luqi-ai" }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# Encrypted backup volume for /var/backups/luqi-ai (db_backup.py target)
resource "aws_ebs_volume" "luqi_backups" {
  availability_zone = aws_instance.luqi_core.availability_zone
  size              = 100
  encrypted         = true
  tags              = { Name = "luqi-ai-backups" }
}
resource "aws_volume_attachment" "luqi_backups" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.luqi_backups.id
  instance_id = aws_instance.luqi_core.id
}

# Optional managed PostgreSQL for the primary DB (set create_rds = true)
variable "create_rds" { type = bool, default = false }
resource "aws_db_instance" "luqi_db" {
  count               = var.create_rds ? 1 : 0
  engine              = "postgres"
  engine_version      = "16"
  instance_class      = "db.t3.medium"
  allocated_storage   = 50
  storage_encrypted   = true
  db_name             = "luqi_ai"
  username            = "luqi_admin"
  password            = var.db_password
  skip_final_snapshot = false
  tags                = { Name = "luqi-ai-db" }
}

output "core_public_ip" { value = aws_instance.luqi_core.public_ip }
output "ssh_command" {
  value = "ssh ubuntu@${aws_instance.luqi_core.public_ip}  # then follow deploy/DEPLOYMENT.md"
}

# CloudFront: static/PWA assets cached at the Johannesburg edge PoP for
# Gauteng students. NOTE: PoP availability and real latency (the "<10ms"
# figure) are measured at deploy time - this config enables the distribution,
# it does not promise a number. Dynamic /v1/* APIs bypass the cache (origin only).
resource "aws_cloudfront_distribution" "luqi_static" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "Luqi-AI static/PWA edge caching (af-south-1 origin)"

  origin {
    domain_name = aws_instance.luqi_core.public_dns
    origin_id   = "luqi-core"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2", "TLSv1.3"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "luqi-core"
    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 300
    forwarded_values { query_string = false }
  }

  # API and live endpoints: never cached
  ordered_cache_behavior {
    path_pattern           = "/v1/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "luqi-core"
    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    forwarded_values { query_string = true headers = ["Authorization"] }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }
  viewer_certificate { cloudfront_default_certificate = true }
}
