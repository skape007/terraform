resource "aws_dynamodb_table" "schedule" {
  name         = local.schedule_table_name
  billing_mode = var.schedule_table_billing_mode

  hash_key = var.schedule_table_hash_key

  attribute {
    name = var.schedule_table_hash_key
    type = "S"
  }

  attribute {
    name = var.schedule_table_gsi_hash_key
    type = "S"
  }

  global_secondary_index {
    name            = var.schedule_table_gsi_name
    hash_key        = var.schedule_table_gsi_hash_key
    projection_type = "ALL"
  }
}

