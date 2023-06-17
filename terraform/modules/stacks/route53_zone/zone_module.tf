module "zone" {
  source = "../../components/route53_zone"

  domain_name = var.domain_name
  hosted_zone_records = var.hosted_zone_records
}