variable "project_name" {
  description = "Project prefix."
  type        = string
}

variable "environment" {
  description = "Environment suffix."
  type        = string
}

variable "state_machine_name" {
  description = "State machine name."
  type        = string
}

variable "function_arn" {
  description = "Lambda ARN invoked by both states."
  type        = string
}

variable "function_name" {
  description = "Lambda name. Kept so a future permission can target the function without the ARN."
  type        = string
}

variable "sfn_role_arn" {
  description = "Role ARN attached to the state machine."
  type        = string
}

variable "sfn_role_name" {
  description = "Role name that receives lambda:InvokeFunction."
  type        = string
}

variable "events_role_arn" {
  description = "Role ARN EventBridge uses to start an execution."
  type        = string
}

variable "events_role_name" {
  description = "Role name that receives states:StartExecution."
  type        = string
}

variable "schedule_expression" {
  description = "EventBridge schedule expression."
  type        = string
}
