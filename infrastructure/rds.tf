resource "aws_db_subnet_group" "mlflow" {
  name       = "${var.cluster_name}-mlflow-db-subnets"
  subnet_ids = aws_subnet.public[*].id

  tags = { Name = "${var.cluster_name}-mlflow-db-subnets" }
}

resource "aws_security_group" "mlflow_rds" {
  name_prefix = "${var.cluster_name}-mlflow-rds-"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.cluster_name}-mlflow-rds-sg" }
}

resource "random_password" "mlflow_db" {
  length  = 20
  special = false
}

resource "aws_secretsmanager_secret" "mlflow_db" {
  name = "${var.cluster_name}/mlflow/db-credentials"
}

resource "aws_secretsmanager_secret_version" "mlflow_db" {
  secret_id = aws_secretsmanager_secret.mlflow_db.id
  secret_string = jsonencode({
    username = "mlflow_admin"
    password = random_password.mlflow_db.result
    dbname   = "mlflow"
  })
}

resource "aws_db_instance" "mlflow" {
  identifier     = "${var.cluster_name}-mlflow-db"
  engine         = "postgres"
  engine_version = "15"

  # Sandbox limits: t3/t4g micro-medium only, no provisioned IOPS, max 50GB
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "mlflow"
  username = "mlflow_admin"
  password = random_password.mlflow_db.result

  db_subnet_group_name   = aws_db_subnet_group.mlflow.name
  vpc_security_group_ids = [aws_security_group.mlflow_rds.id]

  multi_az                = false
  publicly_accessible     = false
  skip_final_snapshot     = true
  deletion_protection     = false
  backup_retention_period = 0

  tags = { Project = "mlops-tourism", Component = "mlflow" }
}
