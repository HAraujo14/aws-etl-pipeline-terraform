output "state_machine_arn" {
  description = "State machine ARN."
  value       = aws_sfn_state_machine.pipeline.arn
}

output "schedule_rule_name" {
  description = "EventBridge rule name."
  value       = aws_cloudwatch_event_rule.daily.name
}
