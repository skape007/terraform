resource "aws_cloudwatch_event_rule" "hourly" {
  name                = "per-job-hourly"
  schedule_expression = "cron(0 * * * ? *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "hourly" {
  rule      = aws_cloudwatch_event_rule.hourly.name
  arn       = aws_lambda_function.scheduler.arn
  target_id = "PerJobScheduler"
}

resource "aws_lambda_permission" "events_invoke" {
  statement_id  = "AllowExecutionFromEvents"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.hourly.arn
}

