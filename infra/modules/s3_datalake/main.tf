resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "this" {
  # Versioning stays off. A re-run overwrites the same daily keys, and
  # versioning would keep every overwrite until a separate rule deleted it.
  bucket        = "${var.project_name}-${var.environment}-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "expire-raw"
    status = "Enabled"

    filter {
      prefix = "${var.raw_prefix}/"
    }

    expiration {
      days = var.raw_expiration_days
    }
  }

  rule {
    id     = "expire-quality"
    status = "Enabled"

    filter {
      prefix = "${var.quality_prefix}/"
    }

    expiration {
      days = var.quality_expiration_days
    }
  }

  rule {
    id     = "expire-curated"
    status = "Enabled"

    filter {
      prefix = "${var.curated_prefix}/"
    }

    expiration {
      days = var.curated_expiration_days
    }
  }

  rule {
    id     = "expire-athena-results"
    status = "Enabled"

    filter {
      prefix = "${var.athena_results_prefix}/"
    }

    expiration {
      days = var.athena_results_expiration_days
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {
      prefix = ""
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
