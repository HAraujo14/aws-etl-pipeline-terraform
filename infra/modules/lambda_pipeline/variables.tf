variable "function_name" {
  description = "Lambda function name."
  type        = string
}

variable "role_arn" {
  description = "Execution role ARN."
  type        = string
}

variable "image_uri" {
  description = "ECR image URI, including the tag."
  type        = string
}

variable "memory_mb" {
  description = "Lambda memory in MB."
  type        = number
}

variable "timeout_seconds" {
  description = "Lambda timeout in seconds."
  type        = number
}

variable "log_retention_days" {
  description = "Retention for the function log group."
  type        = number
}

variable "bucket_name" {
  description = "Data lake bucket name passed to the function."
  type        = string
}

variable "raw_prefix" {
  description = "Raw prefix."
  type        = string
}

variable "curated_prefix" {
  description = "Curated prefix."
  type        = string
}

variable "quality_prefix" {
  description = "Quality-report prefix."
  type        = string
}

variable "forecast_days" {
  description = "Open-Meteo forecast_days."
  type        = number
}

variable "locations" {
  description = "Locations encoded into LOCATIONS_JSON."
  type = list(object({
    location_id = string
    latitude    = number
    longitude   = number
  }))
}
