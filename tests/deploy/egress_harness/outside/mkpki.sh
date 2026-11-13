#!/bin/bash
# R3 G2 harness: a throwaway test CA and two leaf certificates. Output stays in the harness
# work directory (never in the repository). The names are reserved `.invalid` names.
#   mkpki.sh <outdir> <fqdn> <wrong-name>
set -euo pipefail
OUT=$1; FQDN=$2; WRONG=$3
mkdir -p "$OUT"; cd "$OUT"
[ -f ca.key ] || openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -days 30 \
  -subj "/CN=CLM R3 G2 HARNESS TEST CA" -keyout ca.key -out ca.pem \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
leaf() {
  local name=$1 file=$2
  openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -subj "/CN=$name" \
    -keyout "$file.key" -out "$file.csr" 2>/dev/null
  printf 'subjectAltName=DNS:%s\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n' "$name" > "$file.ext"
  openssl x509 -req -in "$file.csr" -CA ca.pem -CAkey ca.key -CAcreateserial -days 30 \
    -extfile "$file.ext" -out "$file.pem" 2>/dev/null
}
leaf "$FQDN" gt
leaf "$WRONG" wrong
openssl x509 -noout -subject -fingerprint -sha256 -in ca.pem
