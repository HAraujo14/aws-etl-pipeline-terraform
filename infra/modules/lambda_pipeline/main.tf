resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "pipeline" {
  function_name = var.function_name
  role          = var.role_arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = var.timeout_seconds
  memory_size   = var.memory_mb
  architectures = ["x86_64"]

  # One reserved execution keeps a bug from fanning out into more invocations.
  reserved_concurrent_executions = 1

  environment {
    variables = {
      STORAGE_BACKEND         = "s3"
      S3_BUCKET               = var.bucket_name
      RAW_PREFIX              = var.raw_prefix
      CURATED_PREFIX          = var.curated_prefix
      QUALITY_PREFIX          = var.quality_prefix
      FORECAST_DAYS           = tostring(var.forecast_days)
      LOCATIONS_JSON          = jsonencode(var.locations)
      OPEN_METEO_BASE_URL     = "https://api.open-meteo.com/v1/forecast"
      LOG_LEVEL               = "INFO"
      QUALITY_MAX_NULL_RATIO  = "0.05"
      REQUEST_TIMEOUT_SECONDS = "30"
    }
  }

  depends_on = [aws_cloudwatch_log_group.pipeline]
}

resource "aws_cloudwatch_metric_alarm" "errors" {
  alarm_name          = "${var.function_name}-errors"
  alarm_description   = "The weather ETL Lambda returned an error."
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.pipeline.function_name
  }
}
