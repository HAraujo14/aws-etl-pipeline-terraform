locals {
  function_name      = "${var.project_name}-${var.environment}-pipeline"
  state_machine_name = "${var.project_name}-${var.environment}-orchestrator"
}

module "datalake" {
  source = "./modules/s3_datalake"

  project_name                   = var.project_name
  environment                    = var.environment
  raw_prefix                     = var.raw_prefix
  quality_prefix                 = var.quality_prefix
  athena_results_prefix          = var.athena_results_prefix
  curated_prefix                 = var.curated_prefix
  raw_expiration_days            = 30
  quality_expiration_days        = 30
  athena_results_expiration_days = 7
  curated_expiration_days        = 365
}

module "ecr" {
  source = "./modules/ecr"

  repository_name = local.function_name
}

module "iam" {
  source = "./modules/iam"

  project_name   = var.project_name
  environment    = var.environment
  bucket_arn     = module.datalake.bucket_arn
  function_name  = local.function_name
  raw_prefix     = var.raw_prefix
  curated_prefix = var.curated_prefix
  quality_prefix = var.quality_prefix
}

module "glue_athena" {
  source = "./modules/glue_athena"

  project_name          = var.project_name
  environment           = var.environment
  bucket_name           = module.datalake.bucket_name
  curated_prefix        = var.curated_prefix
  athena_results_prefix = var.athena_results_prefix
  database_name         = var.glue_database_name
  table_name            = var.glue_table_name
  bytes_scanned_cutoff  = var.athena_bytes_scanned_cutoff
}

module "pipeline" {
  count  = var.image_pushed ? 1 : 0
  source = "./modules/lambda_pipeline"

  function_name      = local.function_name
  role_arn           = module.iam.lambda_role_arn
  image_uri          = "${module.ecr.repository_url}:${var.image_tag}"
  memory_mb          = var.lambda_memory_mb
  timeout_seconds    = var.lambda_timeout_seconds
  log_retention_days = var.log_retention_days
  bucket_name        = module.datalake.bucket_name
  raw_prefix         = var.raw_prefix
  curated_prefix     = var.curated_prefix
  quality_prefix     = var.quality_prefix
  forecast_days      = var.forecast_days
  locations          = var.locations
}

module "orchestration" {
  count  = var.image_pushed ? 1 : 0
  source = "./modules/orchestration"

  project_name        = var.project_name
  environment         = var.environment
  state_machine_name  = local.state_machine_name
  function_arn        = module.pipeline[0].function_arn
  function_name       = module.pipeline[0].function_name
  sfn_role_arn        = module.iam.sfn_role_arn
  sfn_role_name       = module.iam.sfn_role_name
  events_role_arn     = module.iam.events_role_arn
  events_role_name    = module.iam.events_role_name
  schedule_expression = var.schedule_expression
}
