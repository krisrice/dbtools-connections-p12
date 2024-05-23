const common = require("oci-common");
const identity = require("oci-identity");
const dbtools = require("oci-databasetools");
const secrets = require("oci-secrets");
const openssl = require('openssl-wrapper');
const fs = require('node:fs');
const oracledb = require('oracledb');
const { filestorage } = require("oci-sdk");


// compartment id
compartment_id = 'ocid1.tenancy.oc1..xxx'
// dbConnection_OCID
conn_id = 'ocid1.databasetoolsconnection.oc1.iad.xxx'
// oci profile
ociConfig = "~/.oci/config";
ociProfile = 'xxx';

//
// hopefully a much better way but this is what I found
//

function convertP12toPEM(pkcs12File,callback){
    fs.writeFile('ewallet.p12',Buffer.from( pkcs12File, 'base64'), { flag: 'w+' }, err => {});
    openssl.exec('pkcs12', {in: 'ewallet.p12', passout: `pass:${pkcs12Passwd}`,passin: `pass:${pkcs12Passwd}`},
    function(err, buffer) {
       console.log(err);
       results = buffer.toString();
       const lines = results.split("\n");
       filteredFile = '';
       isCert = false;
       const certs = [];
       lines.forEach(line => {
           if ( line.startsWith("-----BEGIN")) {
               isCert = true;
           }
           if ( isCert ){
               filteredFile = filteredFile + (filteredFile == ""? "": "\n") + line;  
           } 
           if ( line.startsWith("-----END")) {
               isCert = false;
               certs.push(filteredFile)
               filteredFile=""
           }
       })
       fs.writeFile('ewallet.pem',certs[0] + "\n" +
                                  certs[3]  + "\n" +
                                  certs[1]  + "\n" + 
                                  certs[2]  + "\n", { flag: 'w+' }, err => {});
       callback();
   });
}


(async () => {

    // JavaScript
    const provider = new common.ConfigFileAuthenticationDetailsProvider(
        ociConfig,
        ociProfile
    );

    const dbc = new dbtools.DatabaseToolsClient({authenticationDetailsProvider:provider});
    const secretsClient = new secrets.SecretsClient({authenticationDetailsProvider:provider});

    req = {
            databaseToolsConnectionId : conn_id
        }

    resp = await dbc.getDatabaseToolsConnection(req);

    dbUsername = resp.databaseToolsConnection.userName;
    connectionString = resp.databaseToolsConnection.connectionString;
    passwdOCID = resp.databaseToolsConnection.userPassword.secretId;
    pkcs12OCID = resp.databaseToolsConnection.keyStores[0].keyStoreContent.secretId;
    pkcs12PasswdOCID = resp.databaseToolsConnection.keyStores[0].keyStorePassword.secretId;

    passwdResp = await secretsClient.getSecretBundle({secretId:passwdOCID})
    passwd = Buffer.from(passwdResp.secretBundle.secretBundleContent.content.toString('utf8'), 'base64').toString('ascii');
    pkcs12PasswdResp = await secretsClient.getSecretBundle({secretId:pkcs12PasswdOCID})
    pkcs12Passwd = Buffer.from(pkcs12PasswdResp.secretBundle.secretBundleContent.content.toString('utf8'), 'base64').toString('ascii');

    pkcs12FileResp = await secretsClient.getSecretBundle({secretId:pkcs12OCID})


    pkcs12File = pkcs12FileResp.secretBundle.secretBundleContent.content;

    convertP12toPEM(pkcs12File, async function (){

        const connection = await oracledb.getConnection ({
            user            : dbUsername,
            password        : passwd,
            connectString   : connectionString,
            walletLocation  : ".",
            walletPassword  : pkcs12Passwd,
            retryCount      : 0,
            retryDelay      : 0 
        });
    
        const result = await connection.execute(
            `select * from dual`
        );
    
        console.log(result.rows);
        await connection.close();
    });


    
     console.log(pkcs12Passwd)

    })();