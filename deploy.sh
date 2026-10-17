#!/usr/bin/env bash
# Deploy ClaimSat to Cloud Run: the API first, then the web app pointing at it.
#
#   ./deploy.sh PROJECT_ID OFFICER_ACCESS_CODE [GEMINI_MODEL]
#
# Needs: gcloud signed in, the APIs enabled and the claimsat-api service
# account, bucket and dataset created (see README "Google Cloud setup").
set -euo pipefail

PROJECT_ID="${1:?usage: ./deploy.sh PROJECT_ID OFFICER_ACCESS_CODE [GEMINI_MODEL]}"
OFFICER_CODE="${2:?usage: ./deploy.sh PROJECT_ID OFFICER_ACCESS_CODE [GEMINI_MODEL]}"
GEMINI_MODEL="${3:-gemini-2.5-flash}"
REGION="asia-south1"
SA="claimsat-api@${PROJECT_ID}.iam.gserviceaccount.com"
cd "$(dirname "$0")"

echo "==> Deploying claimsat-api"
gcloud run deploy claimsat-api \
  --project "$PROJECT_ID" --region "$REGION" --source api \
  --service-account "$SA" --allow-unauthenticated \
  --memory 1Gi --timeout 120 \
  --set-env-vars "GCP_PROJECT=${PROJECT_ID},VERTEX_LOCATION=us-central1,GEMINI_MODEL=${GEMINI_MODEL},GCS_BUCKET=${PROJECT_ID}-claimsat,BQ_DATASET=claimsat,DEMO_MODE=true,OFFICER_ACCESS_CODE=${OFFICER_CODE}"

API_URL="$(gcloud run services describe claimsat-api --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)')"
echo "    API: $API_URL"

echo "==> Deploying claimsat-web"
gcloud run deploy claimsat-web \
  --project "$PROJECT_ID" --region "$REGION" --source web \
  --allow-unauthenticated --memory 512Mi \
  --set-env-vars "API_URL=${API_URL}"

WEB_URL="$(gcloud run services describe claimsat-web --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)')"
echo
echo "Done."
echo "  App:    $WEB_URL"
echo "  Status: $WEB_URL/status"
