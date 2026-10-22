variable "project_name" {
  description = "Project prefix for role names."
  type        = string
}

variable "environment" {
  description = "Environment suffix for role names."
  type        = string
}

variable "bucket_arn" {
  description = "Data lake bucket ARN."
  type        = string
}

variable "function_name" {
  description = "Lambda function name. Used to scope the log-group ARN before the function exists."
  type        = string
}

variable "raw_prefix" {
  description = "Raw JSON prefix."
  type        = string
}

variable "curated_prefix" {
  description = "Curated Parquet prefix."
  type        = string
}

variable "quality_prefix" {
  description = "Quality report prefix."
  type        = string
}
