locals {
  # Glue partition projection reads this template literally, so Terraform must
  # emit a single dollar sign in front of {ingest_date}.
  storage_template = "s3://${var.bucket_name}/${var.curated_prefix}/ingest_date=$${ingest_date}"
}

resource "aws_glue_catalog_database" "this" {
  name        = var.database_name
  description = "Curated Open-Meteo observations for the weather ETL portfolio project."
}

resource "aws_glue_catalog_table" "observations" {
  name          = var.table_name
  database_name = aws_glue_catalog_database.this.name
  table_type    = "EXTERNAL_TABLE"
  description   = "Hourly forecast observations. Partitioned by the UTC date the pipeline ran."

  parameters = {
    EXTERNAL                               = "TRUE"
    classification                         = "parquet"
    "parquet.compression"                  = "SNAPPY"
    "projection.enabled"                   = "true"
    "projection.ingest_date.type"          = "date"
    "projection.ingest_date.format"        = "yyyy-MM-dd"
    "projection.ingest_date.range"         = "2024-01-01,NOW"
    "projection.ingest_date.interval"      = "1"
    "projection.ingest_date.interval.unit" = "DAYS"
    "storage.location.template"            = local.storage_template
  }

  storage_descriptor {
    location      = "s3://${var.bucket_name}/${var.curated_prefix}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name    = "observation_time"
      type    = "timestamp"
      comment = "Forecast hour in UTC."
    }
    columns {
      name    = "location_id"
      type    = "string"
      comment = "Configured location id, for example berlin."
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name    = "elevation_m"
      type    = "double"
      comment = "Elevation reported by Open-Meteo, in meters."
    }
    columns {
      name    = "temperature_c"
      type    = "double"
      comment = "Air temperature at 2 meters, Celsius."
    }
    columns {
      name    = "relative_humidity_pct"
      type    = "double"
      comment = "Relative humidity at 2 meters, percent."
    }
    columns {
      name    = "precipitation_mm"
      type    = "double"
      comment = "Precipitation during the hour, millimeters."
    }
    columns {
      name    = "wind_speed_kmh"
      type    = "double"
      comment = "Wind speed at 10 meters, kilometers per hour."
    }
    columns {
      name    = "data_source"
      type    = "string"
      comment = "Constant open-meteo."
    }
    columns {
      name    = "ingested_at"
      type    = "timestamp"
      comment = "UTC time the transform wrote this batch."
    }
  }

  partition_keys {
    name    = "ingest_date"
    type    = "date"
    comment = "UTC date the pipeline landed the batch. Not an observation date."
  }
}

resource "aws_athena_workgroup" "this" {
  name          = "${var.project_name}-${var.environment}"
  description   = "Workgroup for the weather ETL demo. Queries that would scan more than the cutoff are rejected."
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = false
    bytes_scanned_cutoff_per_query     = var.bytes_scanned_cutoff

    result_configuration {
      output_location = "s3://${var.bucket_name}/${var.athena_results_prefix}/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}
