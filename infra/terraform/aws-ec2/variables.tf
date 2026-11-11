variable "aws_region" {
  description = "Región de AWS donde se desplegará la demo."
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "Tipo de instancia EC2 para la demo."
  type        = string
  default     = "t3.micro"
}

variable "http_allowed_cidr" {
  description = "CIDR autorizado para acceder a la aplicación por HTTP."
  type        = string
  default     = "0.0.0.0/0"
}

variable "artifact_path" {
  description = "Ruta al paquete generado por make package-stage-3."
  type        = string
  default     = "build/finance-platform-stage-3.tar.gz"
}
