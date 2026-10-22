variable "project_name" {
  description = "Project prefix for the Athena workgroup."
  type        = string
}

variable "environment" {
  description = "Environment suffix for the Athena workgroup."
  type        = string
}

variable "bucket_name" {
  description = "Bucket that holds curated Parquet and Athena results."
  type        = string
}

variable "curated_prefix" {
  description = "Curated prefix, without a trailing slash."
  type        = string
}

variable "athena_results_prefix" {
  description = "Prefix for query results."
  type        = string
}

variable "database_name" {
  description = "Glue database name."
  type        = string
}

variable "table_name" {
  description = "Glue table name."
  type        = string
}

variable "bytes_scanned_cutoff" {
  description = "Maximum bytes a query in this workgroup may scan."
  type        = number
}
