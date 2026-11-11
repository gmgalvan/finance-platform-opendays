#!/usr/bin/env bash
# Despliega en Kind la versión publicada por el CI para el último commit de main.
# Uso: deploy/kind/release.sh [sha-<commit>]
set -euo pipefail

OWNER="gmgalvan"
NAMESPACE="finance"
COMPONENTS=(api frontend)

if [[ $# -ge 1 ]]; then
  TAG="$1"
else
  git fetch --quiet origin main
  TAG="sha-$(git rev-parse origin/main | cut -c1-7)"
fi

image_exists() {
  local repository="${OWNER}/finance-platform-$1"
  local token
  token=$(curl -fsS "https://ghcr.io/token?scope=repository:${repository}:pull" | sed -E 's/.*"token":"([^"]+)".*/\1/')
  curl -fsS -o /dev/null \
    -H "Authorization: Bearer ${token}" \
    -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json" \
    "https://ghcr.io/v2/${repository}/manifests/${TAG}"
}

echo "Versión a desplegar: ${TAG}"
for component in "${COMPONENTS[@]}"; do
  printf "Esperando la imagen finance-platform-%s:%s en GHCR" "$component" "$TAG"
  for attempt in $(seq 1 60); do
    if image_exists "$component"; then
      echo " ✓"
      break
    fi
    if [[ $attempt -eq 60 ]]; then
      echo " ✗ no apareció en 5 minutos. ¿Terminó el CI en main?" >&2
      exit 1
    fi
    printf "."
    sleep 5
  done
done

echo
echo "Versión actual en el clúster:"
kubectl -n "$NAMESPACE" get deployments -o custom-columns='DEPLOYMENT:.metadata.name,IMAGEN:.spec.template.spec.containers[0].image'
echo

for component in "${COMPONENTS[@]}"; do
  kubectl -n "$NAMESPACE" set image "deployment/${component}" \
    "${component}=ghcr.io/${OWNER}/finance-platform-${component}:${TAG}"
  kubectl -n "$NAMESPACE" annotate "deployment/${component}" --overwrite \
    "kubernetes.io/change-cause=Release ${TAG}"
done

for component in "${COMPONENTS[@]}"; do
  kubectl -n "$NAMESPACE" rollout status "deployment/${component}" --timeout=180s
done

echo
echo "✓ ${TAG} desplegada"
kubectl -n "$NAMESPACE" get deployments -o custom-columns='DEPLOYMENT:.metadata.name,IMAGEN:.spec.template.spec.containers[0].image,LISTOS:.status.readyReplicas'
