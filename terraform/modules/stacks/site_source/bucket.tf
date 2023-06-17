# Defining the s3 bucket for this site source,
# as well as any policies related to it

# Our S3 bucket
resource "aws_s3_bucket" "siteSourceBucket" {
  bucket = "${var.bucket_name}-${local.account_id}"
}

# Allowing our site source's cloudfront distribution to access
# this bucket's objects
resource "aws_s3_bucket_policy" "allowSiteSourceDistributionToAccessSiteBucket" {
  bucket = aws_s3_bucket.siteSourceBucket.id
  policy = data.aws_iam_policy_document.allowSiteSourceDistributionToAccessSiteBucket.json
}

# The actual IAM policy to enable this
data "aws_iam_policy_document" "allowSiteSourceDistributionToAccessSiteBucket" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]

    principals {
      type = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test = "StringEquals"
      variable = "aws:SourceArn"
      values = [
        "arn:aws:cloudfront::${local.account_id}:distribution/${aws_cloudfront_distribution.siteSourceDistribution.id}"
      ]
    }

    resources = [
      "${aws_s3_bucket.siteSourceBucket.arn}/*",
      aws_s3_bucket.siteSourceBucket.arn
    ]
  }
}

# This resource disables ACLs and allows us to use bucket
# policies instead. This is the reccomended way to configure this
resource "aws_s3_bucket_ownership_controls" "prodBucketOwnershipControls" {
  bucket = aws_s3_bucket.siteSourceBucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Blocks public access to objects
resource "aws_s3_bucket_public_access_block" "prodBucketPublicAccessConfig" {
  bucket = aws_s3_bucket.siteSourceBucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}