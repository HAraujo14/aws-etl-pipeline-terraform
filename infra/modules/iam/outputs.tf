output "lambda_role_arn" {
  description = "Execution role for the pipeline Lambda."
  value       = aws_iam_role.lambda.arn
}

output "sfn_role_arn" {
  description = "Role Step Functions assumes to invoke the Lambda."
  value       = aws_iam_role.sfn.arn
}

output "sfn_role_name" {
  description = "Role name, used when the orchestration module attaches the invoke policy."
  value       = aws_iam_role.sfn.name
}

output "events_role_arn" {
  description = "Role EventBridge assumes to start the state machine."
  value       = aws_iam_role.events.arn
}

output "events_role_name" {
  description = "Role name, used when the orchestration module attaches StartExecution."
  value       = aws_iam_role.events.name
}
