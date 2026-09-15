variable "aws_region" {
  description = "Sovereign region: AWS Cape Town"
  type        = string
  default     = "af-south-1"
}

variable "instance_type" {
  type    = string
  default = "t3.large"   # headroom for Docker sandboxes (500 x 512MB cap requires more - size per plan)
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH deploy access"
  type        = string
}

variable "db_password" {
  description = "RDS master password - pass via TF_VAR_db_password env, NEVER commit"
  type        = string
  sensitive   = true
}
