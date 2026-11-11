# Stage 3: despliegue en AWS EC2

Esta etapa despliega Finance Platform en una instancia Amazon Linux 2023 mediante Terraform. La aplicación conserva sus tres capas dentro de Docker:

```text
Internet → EC2:80 → Nginx → API → PostgreSQL
```

## Recursos

- Una instancia EC2 `t3.micro` con disco gp3 cifrado.
- Un security group que permite solamente HTTP de entrada.
- Un rol de instancia con acceso mediante Systems Manager.
- Un bucket S3 privado para entregar el artefacto de la aplicación.
- Un volumen Docker para persistir PostgreSQL dentro de la VM.

No se abre el puerto SSH. La administración utiliza AWS Systems Manager Session Manager.

## Desplegar

```bash
make package-stage-3
make terraform-stage-3-init
make terraform-stage-3-plan
make terraform-stage-3-apply
```

Terraform muestra `application_url` al terminar. El bootstrap puede tardar algunos minutos porque instala Docker y construye las imágenes en EC2.

## Verificar

```bash
make terraform-stage-3-output
```

Abrir la URL y consultar `/api/health` y `/api/metrics`.

Para revisar el bootstrap mediante SSM:

```bash
aws ssm start-session --target INSTANCE_ID --region us-east-1
```

Dentro de la instancia:

```bash
sudo tail -f /var/log/finance-platform-bootstrap.log
sudo docker ps
```

## Eliminar los recursos

Cuando termine la demostración:

```bash
make terraform-stage-3-destroy
```

Esto elimina la EC2, el bucket de artefactos, el security group y los recursos IAM creados por este módulo.
