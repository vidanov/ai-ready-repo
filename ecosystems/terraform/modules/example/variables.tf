variable "queue_name" {
  description = "Name of the SQS queue"
  type        = string
}

variable "retention_days" {
  description = "Message retention period in days"
  type        = number
  default     = 14
}

variable "visibility_timeout" {
  description = "Visibility timeout in seconds"
  type        = number
  default     = 300
}

variable "max_receive_count" {
  description = "Number of receives before message goes to DLQ"
  type        = number
  default     = 3
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
