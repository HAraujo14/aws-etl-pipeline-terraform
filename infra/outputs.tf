output "bucket_name" {
  description = "Data lake bucket."
  value       = module.datalake.bucket_name
}

output "ecr_repository_url" {
  description = "Push the Lambda image here before setting image_pushed=true."
  value       = module.ecr.repository_url
}

output "glue_database_name" {
  description = "Glue database for the curated table."
  value       = module.glue_athena.database_name
}

output "glue_table_name" {
  description = "Glue table name. Query it as database.table from the Athena workgroup."
  value       = module.glue_athena.table_name
}

output "athena_workgroup" {
  description = "Athena workgroup with a 10 MB scan cutoff."
  value       = module.glue_athena.workgroup_name
}

output "lambda_function_name" {
  description = "Pipeline Lambda. Null until image_pushed is true."
  value       = one(module.pipeline[*].function_name)
}

output "state_machine_arn" {
  description = "Step Functions state machine. Null until image_pushed is true."
  value       = one(module.orchestration[*].state_machine_arn)
}

output "sample_athena_query" {
  description = "Query to run in the Athena workgroup after at least one successful curated write."
  value       = "SELECT location_id, avg(temperature_c) AS avg_temperature_c FROM ${module.glue_athena.database_name}.${module.glue_athena.table_name} WHERE ingest_date = current_date GROUP BY location_id ORDER BY location_id;"
}
