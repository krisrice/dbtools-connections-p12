import oci
import base64
import oracledb
from oci.config import from_file, validate_config
from zipfile import ZipFile
import io
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography import x509

tempWalletPassword="Change-Example-Passw0rd!"

 # Load an OCI config with the DEFAULT profile
oci_config = from_file(file_location="~/.oci/config", profile_name="xxx")

compartment_id = 'ocid1.tenancy.oc1..xxx'
conn_id = 'ocid1.databasetoolsconnection.oc1.iad.xxx'

dbtools_client = oci.database_tools.DatabaseToolsClient(config=oci_config)

dbt_resp = dbtools_client.get_database_tools_connection(conn_id)

secrets_client = oci.secrets.SecretsClient(oci_config)

secret_resp = secrets_client.get_secret_bundle(secret_id=dbt_resp.data.user_password.secret_id,
                                             stage="LATEST")

dbOCID = dbt_resp.data.related_resource.identifier

username = dbt_resp.data.user_name

connString = dbt_resp.data.connection_string

userPassword = base64.b64decode(secret_resp.data.secret_bundle_content.content).decode('utf-8')

print(username)
print(userPassword)
print(connString)

def getWalletStripPassword(tempWalletPassword, oci_config, dbOCID):
    DBclient = oci.database.DatabaseClient(config=oci_config)

    db_wallet = oci.database.models.GenerateAutonomousDatabaseWalletDetails(
        password=tempWalletPassword
    )
    db_wallet_response = DBclient.generate_autonomous_database_wallet(
        autonomous_database_id=dbOCID,
        generate_autonomous_database_wallet_details=db_wallet,
    )
    mem_file = io.BytesIO(db_wallet_response.data.content)

    input_zip = ZipFile(mem_file)


    with input_zip as zip_ref:
        zip_ref.extractall("./wallet")

# Path to the PEM file
    pem_file_path = './wallet/ewallet.pem'
# Password for the PEM file
    password = bytes(tempWalletPassword,"utf-8")

# Read the PEM file
    with open(pem_file_path, 'rb') as pem_file:
        pem_data = pem_file.read()

    certs = []
    for cert in pem_data.split(b'-----END CERTIFICATE-----'):
        if b'-----BEGIN CERTIFICATE-----' in cert:
            cert += b'-----END CERTIFICATE-----'
            certificate = x509.load_pem_x509_certificate(cert)
            certs.append(certificate)

# Load the private key from the PEM file
    private_key = serialization.load_pem_private_key(
        pem_data,
        password=password,
        backend=default_backend()
    )

# Now you can use the private_key object

    pem_data = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Write the PEM data to a file
    pem_file_path = 'wallet2/ewallet.pem'
    with open(pem_file_path, 'wb') as pem_file:
        pem_file.write(pem_data)
        for i, cert in enumerate(certs):        
            pem_file.write(cert.public_bytes(serialization.Encoding.PEM))

getWalletStripPassword(tempWalletPassword, oci_config, dbOCID)


start = time.time()
connection = oracledb.connect(user=username, 
                              password=userPassword,  
                              dsn=connString, 
                              ssl_server_dn_match=False, 
#                              wallet_password="Change-Example-Passw0rd!",
                              wallet_location="./wallet2")
end = time.time()
print(end - start)



# connection = oracledb.connect(user=username, 
#                               password=userPassword,  
#                               dsn=connString, 
#                               ssl_server_dn_match=False, 
# #                              wallet_password="Change-Example-Passw0rd!",
#                               wallet_location="./wallet2")