from OpenSSL import crypto, SSL

VALIDITY = 60*60*24*365*5

def create_cert(cn, san_list=None, sign_key=None, sign_cert=None, ca=False):
    generated_key = crypto.PKey()
    generated_key.generate_key(crypto.TYPE_RSA, 2048)

    generated_req = crypto.X509Req()
    generated_req.get_subject().CN = cn
    generated_req.set_pubkey(generated_key)
    generated_req.sign(generated_key, 'sha1')

    generated_cert = crypto.X509()

    if san_list:
        generated_cert.add_extensions([crypto.X509Extension(
            "subjectAltName", False, ", ".join(san_list)
            )])

    generated_cert.gmtime_adj_notBefore(0)
    generated_cert.gmtime_adj_notAfter(VALIDITY)
    generated_cert.set_subject(generated_req.get_subject())
    generated_cert.set_pubkey(generated_req.get_pubkey())

    issuer_cert = sign_cert if sign_cert else generated_cert
    generated_cert.set_issuer(issuer_cert.get_subject())

    generated_cert.sign(sign_key if sign_key else generated_key, 'sha1')

    if ca:
        generated_cert.add_extensions([
            crypto.X509Extension("basicConstraints", True, "CA:TRUE"),
            crypto.X509Extension("subjectKeyIdentifier", False, "hash", subject=generated_cert),
            ])
        generated_cert.add_extensions([
            crypto.X509Extension("authorityKeyIdentifier", False, "keyid:always", 
                issuer=generated_cert)
            ])

    pem_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, generated_key)
    pem_cert = crypto.dump_certificate(crypto.FILETYPE_PEM, generated_cert)

    return (pem_key, pem_cert, generated_key, generated_cert)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 colorcolumn=100
