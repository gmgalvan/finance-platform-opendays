output "application_url" {
  description = "URL pública de Finance Platform."
  value       = "http://${aws_instance.application.public_ip}"
}

output "instance_id" {
  description = "ID de la instancia para consultas y acceso mediante SSM."
  value       = aws_instance.application.id
}

output "public_ip" {
  description = "Dirección IPv4 pública de la instancia."
  value       = aws_instance.application.public_ip
}

output "artifact_bucket" {
  description = "Bucket privado que contiene el paquete de despliegue."
  value       = aws_s3_bucket.artifacts.id
}

output "verification_commands" {
  description = "Comandos para comprobar la aplicación después del bootstrap."
  value = {
    health  = "curl http://${aws_instance.application.public_ip}/api/health"
    metrics = "curl http://${aws_instance.application.public_ip}/api/metrics"
    ssm     = "aws ssm start-session --target ${aws_instance.application.id} --region ${var.aws_region}"
  }
}
