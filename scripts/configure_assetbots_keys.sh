#!/bin/zsh
set -euo pipefail

services=(
  uk.ac.bham.vrlab.assetbots.it
  uk.ac.bham.vrlab.assetbots.headsets
  uk.ac.bham.vrlab.assetbots.misc
  uk.ac.bham.vrlab.assetbots.storage
  uk.ac.bham.vrlab.assetbots.visitor-cards
)

labels=(
  "VR Lab IT"
  "VR lab headsets"
  "VR Lab Misc"
  "VR Lab In storage"
  "Visitor cards"
)

echo "Create a Reader API key in each Assetbots database first."
echo "Each prompt below is handled by macOS Keychain; the key is not echoed."

for index in {1..5}; do
  service=${services[$index]}
  label=${labels[$index]}
  echo
  echo "Paste the Reader API key for: $label"
  /usr/bin/security add-generic-password \
    -U \
    -a api \
    -s "$service" \
    -l "Assetbots backup — $label" \
    -w
done

echo
echo "Five Assetbots API keys are stored in the login Keychain."
