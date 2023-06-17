# Creates all applicable route 53 records
# for this site-source's distribution. Also
# imports a module the creates our r53 zone,
# which is where we get the our zone_id from

# The following resource auto-creates all records using
# for_each
resource "aws_route53_record" "siteSourceRoute53Records" {
  for_each = toset(var.cloudfront_aliases)

  zone_id = var.route53_zone_id
  name = each.key
  type = "A"

  alias {
    name = aws_cloudfront_distribution.siteSourceDistribution.domain_name
    zone_id = aws_cloudfront_distribution.siteSourceDistribution.hosted_zone_id
    evaluate_target_health = true
  }
}