# Config for our ACM Certificate for this site source

# We need to make this cert in us-east-1, so we need a custom provider
provider "aws" {
  region = "us-east-1"
  alias = "us-east-1"
}

# Creating our ACM Cert; using some terraform functions to
# automatically populate domain names and alt names
resource "aws_acm_certificate" "prodSiteSourceACMCert" {
  provider = aws.us-east-1
  
  # Set domain name to first domain in the cloudfront_aliases list
  domain_name = element(var.cloudfront_aliases, 0)
  # Set alt names to all other aliases; ignore the one where index = 0 obviously
  subject_alternative_names = [for alias in var.cloudfront_aliases: alias if index(var.cloudfront_aliases, alias) != 0]

  validation_method = "DNS"
}

# SSL Cert Records for this ACM Cert
resource "aws_route53_record" "siteSourceACMCertRoute53Record" {
  for_each = {
    for dvo in aws_acm_certificate.prodSiteSourceACMCert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name = each.value.name
  records = [each.value.record]
  ttl = 60
  type = each.value.type
  zone_id = var.route53_zone_id
}

resource "aws_acm_certificate_validation" "prodSiteSourceACMValidation" {
  provider = aws.us-east-1
  certificate_arn         = aws_acm_certificate.prodSiteSourceACMCert.arn
  validation_record_fqdns = [for record in aws_route53_record.siteSourceACMCertRoute53Record : record.fqdn]
}