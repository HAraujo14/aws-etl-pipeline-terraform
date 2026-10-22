variable "project_name" {
  description = "Project prefix used in the bucket name."
  type        = string
}

variable "environment" {
  description = "Environment suffix used in the bucket name."
  type        = string
}

variable "raw_prefix" {
  description = "Prefix whose objects expire first."
  type        = string
}

variable "curated_prefix" {
  description = "Prefix for curated Parquet."
  type        = string
}

variable "quality_prefix" {
  description = "Prefix for quality-report JSON."
  type        = string
}

variable "athena_results_prefix" {
  description = "Prefix for Athena results."
  type        = string
}

variable "raw_expiration_days" {
  description = "Days to keep raw JSON."
  type        = number
}

variable "quality_expiration_days" {
  description = "Days to keep quality reports."
  type        = number
}

variable "athena_results_expiration_days" {
  description = "Days to keep Athena results."
  type        = number
}

variable "curated_expiration_days" {
  description = "Days to keep curated Parquet."
  type        = number
}
