#!/usr/bin/env bash
source "$(dirname "$0")/common.sh"
: "${K3S_LOCAL_IMPORT:?Set K3S_LOCAL_IMPORT=yes only on the reviewed target K3s node}"
[[ "$K3S_LOCAL_IMPORT" == yes ]] || exit 1
command -v docker >/dev/null
command -v k3s >/dev/null
images=()
for service in api-gateway auth-service workflow-service integration-service action-service execution-service rag-service frontend; do
  image="relay/$service:${IMAGE_TAG:-dev}"
  [[ $(docker image inspect "$image" --format '{{.Architecture}}') == amd64 ]] || { echo "Wrong architecture: $image" >&2; exit 1; }
  images+=("$image")
done
# Streams the archive: no duplicate multi-GB tar file on the root disk.
docker save "${images[@]}" | sudo k3s ctr images import -
printf 'Imported existing images. No image was rebuilt. Verify tags match your app AND migration overlays.\n'
