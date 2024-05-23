import com.oracle.bmc.ConfigFileReader;
import com.oracle.bmc.auth.AuthenticationDetailsProvider;
import com.oracle.bmc.auth.ConfigFileAuthenticationDetailsProvider;
import com.oracle.bmc.databasetools.DatabaseToolsClient;

import com.oracle.bmc.databasetools.model.*;

import com.oracle.bmc.databasetools.requests.GetDatabaseToolsConnectionRequest;
import com.oracle.bmc.databasetools.responses.GetDatabaseToolsConnectionResponse;
import com.oracle.bmc.secrets.SecretsClient;
import com.oracle.bmc.secrets.model.Base64SecretBundleContentDetails;
import com.oracle.bmc.secrets.model.SecretBundleContentDetails;
import com.oracle.bmc.secrets.requests.GetSecretBundleRequest;
import oracle.security.pki.OracleWallet;
import oracle.security.pki.textui.OraclePKIGenFunc;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.NoSuchAlgorithmException;
import java.security.UnrecoverableKeyException;
import java.security.cert.CertificateException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Base64;
import java.util.Properties;

public class SampleP12 {
  static String OCI_CONFIG = "~/.oci/config";
  static String OCI_PROFILE ="xxx";
  static String OCI_COMPARTMENT= "ocid1.tenancy.oc1..xxx";
  static String OCI_CONNECTION = "ocid1.databasetoolsconnection.oc1.iad.xxx";


  public static void main(String[] args) throws IOException, UnrecoverableKeyException, CertificateException, NoSuchAlgorithmException, SQLException {
    AuthenticationDetailsProvider provider =
            new ConfigFileAuthenticationDetailsProvider(ConfigFileReader.parseDefault(OCI_PROFILE));

    DatabaseToolsClient dbc= DatabaseToolsClient.builder().build(provider);

    GetDatabaseToolsConnectionResponse dbcResponse = dbc.getDatabaseToolsConnection(
            GetDatabaseToolsConnectionRequest.builder()
                .databaseToolsConnectionId(OCI_CONNECTION)
            .build());

    DatabaseToolsConnectionOracleDatabase x = (DatabaseToolsConnectionOracleDatabase) dbcResponse.getDatabaseToolsConnection();

    String name = x.getDisplayName();
    String username = x.getUserName();
    String connString = x.getConnectionString();
    String userPasswordOCID = ((DatabaseToolsUserPasswordSecretId)x.getUserPassword()).getSecretId();;

    String p12FileOCID = ((DatabaseToolsKeyStoreContentSecretId)x.getKeyStores().get(0).getKeyStoreContent()).getSecretId();
    String p12FilePasswdOCID = ((DatabaseToolsKeyStorePasswordSecretId)x.getKeyStores().get(0).getKeyStorePassword()).getSecretId();
    SecretsClient secretClient = SecretsClient.builder().build(provider);
    String userPasswd = new String(Base64.getDecoder().decode (((Base64SecretBundleContentDetails) secretClient.getSecretBundle(GetSecretBundleRequest.builder().secretId(userPasswordOCID).build()).getSecretBundle().getSecretBundleContent()).getContent().getBytes()));
    String p12Password = new String(Base64.getDecoder().decode (((Base64SecretBundleContentDetails) secretClient.getSecretBundle(GetSecretBundleRequest.builder().secretId(p12FilePasswdOCID).build()).getSecretBundle().getSecretBundleContent()).getContent().getBytes()));
    byte[] p12FileBytes = Base64.getDecoder().decode(
            ((Base64SecretBundleContentDetails) secretClient.getSecretBundle(GetSecretBundleRequest.builder().secretId(p12FileOCID).build()).getSecretBundle().getSecretBundleContent()).getContent().getBytes());

    Files.write(Paths.get("ewallet.p12"),p12FileBytes);

    OracleWallet w = new OracleWallet();
    w = OraclePKIGenFunc.openAWallet("ewallet.p12", p12Password , false, true);

    w.saveSSO();
    java.security.Security.addProvider( new oracle.security.pki.OraclePKIProvider() );

    Properties props = new Properties();
    props.setProperty("user", username);
    props.setProperty("password", userPasswd);

    System.out.println(connString);
    //Single sign on
    props.setProperty("javax.net.ssl.trustStore", "cwallet.sso");
    props.setProperty("javax.net.ssl.trustStoreType","SSO");
    props.setProperty("javax.net.ssl.keyStore","cwallet.sso");
    props.setProperty("javax.net.ssl.keyStoreType","SSO");
    Connection connection = DriverManager.getConnection("jdbc:oracle:thin:@" + connString, props);
    if (connection != null) {
      System.out.println("Connected ! ");
    }
    System.exit(0);



  }
}
