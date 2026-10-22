variable "aws_region" {
  description = "Region for every resource. us-east-1 keeps the demo on the broadest free-tier surface."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short prefix used in resource names. Lowercase letters, digits, and hyphens."
  type        = string
  default     = "weather-etl"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.project_name))
    error_message = "project_name must be 2-31 characters: lowercase letters, digits, and hyphens."
  }
}

variable "environment" {
  description = "Environment name appended to resource names."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z0-9]{2,10}$", var.environment))
    error_message = "environment must be 2-10 lowercase letters or digits."
  }
}

variable "image_tag" {
  description = "Container tag pushed to ECR before image_pushed is set to true."
  type        = string
  default     = "latest"
}

variable "image_pushed" {
  description = "Create the Lambda, schedule, and state machine only after the container image exists in ECR."
  type        = bool
  default     = false
}

variable "raw_prefix" {
  description = "S3 prefix for raw Open-Meteo JSON."
  type        = string
  default     = "raw/weather"
}

variable "curated_prefix" {
  description = "S3 prefix for curated Parquet. This is the Glue table location."
  type        = string
  default     = "curated/weather"
}

variable "quality_prefix" {
  description = "S3 prefix for data-quality reports. Kept outside the curated prefix so Athena does not read JSON."
  type        = string
  default     = "quality/weather"
}

variable "athena_results_prefix" {
  description = "S3 prefix for Athena query results."
  type        = string
  default     = "athena-results"
}

variable "locations" {
  description = "Forecast locations passed to the Lambda as LOCATIONS_JSON."
  type = list(object({
    location_id = string
    latitude    = number
    longitude   = number
  }))
  default = [
    {
      location_id = "berlin"
      latitude    = 52.52
      longitude   = 13.41
    },
    {
      location_id = "sao_paulo"
      latitude    = -23.55
      longitude   = -46.63
    },
    {
      location_id = "new_york"
      latitude    = 40.71
      longitude   = -74.01
    },
  ]
}

variable "forecast_days" {
  description = "Open-Meteo forecast_days value. 1 keeps each run to a single UTC day."
  type        = number
  default     = 1

  validation {
    condition     = var.forecast_days >= 1 && var.forecast_days <= 16
    error_message = "forecast_days must be between 1 and 16."
  }
}

variable "schedule_expression" {
  description = "EventBridge schedule for the state machine. Default is 06:15 UTC every day."
  type        = string
  default     = "cron(15 6 * * ? *)"
}

variable "lambda_memory_mb" {
  description = "Lambda memory. 512 MB is enough for three small frames and pandas."
  type        = number
  default     = 512
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout. The forecast calls are small; the timeout leaves room for a cold start."
  type        = number
  default     = 120
}

variable "log_retention_days" {
  description = "CloudWatch log retention for the Lambda function."
  type        = number
  default     = 14
}

variable "athena_bytes_scanned_cutoff" {
  description = "Athena workgroup cap, in bytes. 10 MiB stops an accidental full-bucket scan."
  type        = number
  default     = 10485760
}

variable "glue_database_name" {
  description = "Glue database that holds the curated table."
  type        = string
  default     = "weather_etl"
}

variable "glue_table_name" {
  description = "Glue table name queried from Athena."
  type        = string
  default     = "hourly_observations"
}
