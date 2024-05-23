import oci
import base64
import os
import oracledb
from oci.config import from_file, validate_config
import time
from cryptography.hazmat.primitives.serialization \
        import pkcs12, Encoding, PrivateFormat, BestAvailableEncryption

# Wallet directory
walletDir = "wallet"
os.mkdir(walletDir)

 # Load an OCI config with the DEFAULT profile
oci_config = from_file(file_location="~/.oci/config", profile_name="KRISRICEIO")
# compartment_id
compartment_id = 'ocid1.tenancy.oc1..aaaaaaaaplcmdlf2lhfcqlkdid6hordp5zj5kb2gr3vhoeh4yghal2jqnqma'
# dbConnection_OCID
conn_id = 'ocid1.databasetoolsconnection.oc1.iad.amaaaaaakl7rxeyawfijlfsgfkx4fcp5sbzd3taa53wohxjpqfvionywp2pa'

# dbtoolsClient
dbtools_client = oci.database_tools.DatabaseToolsClient(config=oci_config)

# get Connection Details
dbt_resp = dbtools_client.get_database_tools_connection(conn_id)

# make a secret Client
secrets_client = oci.secrets.SecretsClient(oci_config)

def getSecret(ocid):
    secret_resp = secrets_client.get_secret_bundle(secret_id=ocid,
                                             stage="LATEST")
    decodedSecret = base64.b64decode(secret_resp.data.secret_bundle_content.content)
    return decodedSecret

# Associated DB's OCID
dbOCID = dbt_resp.data.related_resource.identifier
# DB Username
username = dbt_resp.data.user_name
# DB Connect String
connString = dbt_resp.data.connection_string
# DB User's PAssword
userPassword= getSecret(dbt_resp.data.user_password.secret_id).decode();
# P12/wallet Password
p12Password= getSecret(dbt_resp.data.key_stores[0].key_store_password.secret_id).decode()
# P12 File Contents
p12File = getSecret(dbt_resp.data.key_stores[0].key_store_content.secret_id)


#
# Convert the P12 to a .pem for use as p12 is not directly usable
#
def createPEMFromP12(p12Password,p12File):
    ## Write the p12 to the file system
    p12FileName= os.path.join(walletDir,'ewallet.p12')

    with open(p12FileName, 'wb') as p12_file:
        p12_file.write(p12File)

    ## extract .PEM from the P12
    pem_file_name =   os.path.join(walletDir,"ewallet.pem");

    pkcs12_data = open(p12FileName, "rb").read()
    result = pkcs12.load_key_and_certificates(pkcs12_data,
                                            p12Password.encode())
    private_key, certificate, additional_certificates = result
    encryptor = BestAvailableEncryption(p12Password.encode())

    with open(pem_file_name, "wb") as f:
        f.write(private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8,
                                        encryptor))
        f.write(certificate.public_bytes(Encoding.PEM))
        for cert in additional_certificates:
            f.write(cert.public_bytes(Encoding.PEM))

createPEMFromP12(p12Password,p12File)

connection = oracledb.connect(user=username, 
                              password=userPassword,  
                              dsn=connString, 
                              ssl_server_dn_match=False, 
                              wallet_password=p12Password,
                              wallet_location=walletDir)
with connection.cursor() as cursor:
    for result in cursor.execute("select * from dual"):
        print(result)