data "aws_iam_policy_document" "invoke_lambda" {
  statement {
    sid     = "InvokePipeline"
    effect  = "Allow"
    actions = ["lambda:InvokeFunction"]
    resources = [
      var.function_arn,
      "${var.function_arn}:*",
    ]
  }
}

data "aws_iam_policy_document" "start_execution" {
  statement {
    sid       = "StartPipeline"
    effect    = "Allow"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.pipeline.arn]
  }
}

resource "aws_iam_role_policy" "invoke_lambda" {
  name   = "${var.project_name}-${var.environment}-sfn-invoke"
  role   = var.sfn_role_name
  policy = data.aws_iam_policy_document.invoke_lambda.json
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = var.state_machine_name
  role_arn = var.sfn_role_arn
  type     = "STANDARD"

  definition = templatefile("${path.module}/statemachine.asl.json.tftpl", {
    function_arn = var.function_arn
  })
}

resource "aws_iam_role_policy" "start_execution" {
  name   = "${var.project_name}-${var.environment}-events-start"
  role   = var.events_role_name
  policy = data.aws_iam_policy_document.start_execution.json
}

resource "aws_cloudwatch_event_rule" "daily" {
  name                = "${var.project_name}-${var.environment}-daily"
  description         = "Daily trigger for ${var.function_name}."
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "pipeline" {
  rule     = aws_cloudwatch_event_rule.daily.name
  arn      = aws_sfn_state_machine.pipeline.arn
  role_arn = var.events_role_arn
  input    = jsonencode({ ingest_date = "" })
}
