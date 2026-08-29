# Example module: SQS queue with encryption
#
# Demonstrates AI-ready Terraform patterns:
# - All resources in modules, not root
# - Variables with no environment-specific defaults
# - checkov-compliant defaults (encryption, logging)

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80.0"
    }
  }
}

resource "aws_sqs_queue" "this" {
  name                       = var.queue_name
  message_retention_seconds  = var.retention_days * 86400
  visibility_timeout_seconds = var.visibility_timeout
  sqs_managed_sse_enabled    = true # checkov: CKV_AWS_27 satisfied

  tags = var.tags
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq"
  message_retention_seconds = var.retention_days * 86400
  sqs_managed_sse_enabled   = true

  tags = var.tags
}

resource "aws_sqs_queue_redrive_policy" "this" {
  queue_url = aws_sqs_queue.this.id

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })
}
