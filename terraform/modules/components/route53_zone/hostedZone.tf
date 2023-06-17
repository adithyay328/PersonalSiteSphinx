# Terraform config for the route 53 hosted zone

# Main hosted zone
resource "aws_route53_zone" "hostedZone" {
  name = var.domain_name
}

resource "aws_route53_record" "records" {
  zone_id = aws_route53_zone.hostedZone.zone_id
  
  count = length(var.hosted_zone_records)

  name = var.hosted_zone_records[count.index].name
  type = var.hosted_zone_records[count.index].type
  records = var.hosted_zone_records[count.index].records
  ttl = var.hosted_zone_records[count.index].ttl
}