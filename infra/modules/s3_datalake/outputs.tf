output "bucket_name" {
  description = "Bucket name, including a random suffix so it can be created in any account."
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "Bucket ARN used to scope IAM policies."
  value       = aws_s3_bucket.this.arn
}
