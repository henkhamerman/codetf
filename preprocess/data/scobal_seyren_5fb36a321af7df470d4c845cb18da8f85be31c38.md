Refactoring Types: ['Extract Method']
seyren/core/service/notification/EmailNotificationService.java
/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.seyren.core.service.notification;

import java.util.List;

import javax.inject.Inject;
import javax.inject.Named;
import javax.mail.MessagingException;
import javax.mail.internet.AddressException;
import javax.mail.internet.InternetAddress;
import javax.mail.internet.MimeMessage;
import javax.mail.internet.MimeMessage.RecipientType;

import org.springframework.mail.javamail.JavaMailSender;

import com.seyren.core.domain.Alert;
import com.seyren.core.domain.Check;
import com.seyren.core.domain.Subscription;
import com.seyren.core.domain.SubscriptionType;
import com.seyren.core.exception.NotificationFailedException;
import com.seyren.core.util.config.SeyrenConfig;
import com.seyren.core.util.email.Email;
import com.seyren.core.util.email.EmailHelper;

@Named
public class EmailNotificationService implements NotificationService {
    
    private final JavaMailSender mailSender;
    private final SeyrenConfig seyrenConfig;
    private final EmailHelper emailHelper;
    
    @Inject
    public EmailNotificationService(JavaMailSender mailSender, SeyrenConfig seyrenConfig, EmailHelper emailHelper) {
        this.mailSender = mailSender;
        this.seyrenConfig = seyrenConfig;
        this.emailHelper = emailHelper;
    }
    
    @Override
    public void sendNotification(Check check, Subscription subscription, List<Alert> alerts) {
        
        try {
            Email email = new Email()
                    .withTo(subscription.getTarget())
                    .withFrom(seyrenConfig.getSmtpFrom())
                    .withSubject(emailHelper.createSubject(check))
                    .withMessage(emailHelper.createBody(check, subscription, alerts));
            
            mailSender.send(createMimeMessage(email));
            
        } catch (Exception e) {
            throw new NotificationFailedException("Failed to send notification to " + subscription.getTarget() + " from " + seyrenConfig.getSmtpFrom(), e);
        }
        
    }
    
    private MimeMessage createMimeMessage(Email email) throws AddressException, MessagingException {
        
        MimeMessage mail = mailSender.createMimeMessage();
        InternetAddress senderAddress = new InternetAddress(email.getFrom());
        mail.addRecipient(RecipientType.TO, new InternetAddress(email.getTo()));
        mail.setSender(senderAddress);
        mail.setFrom(senderAddress);
        mail.setText(email.getMessage());
        mail.setSubject(email.getSubject());
        mail.addHeader("Content-Type", "text/html; charset=UTF-8");
        
        return mail;
    }
    
    @Override
    public boolean canHandle(SubscriptionType subscriptionType) {
        return subscriptionType == SubscriptionType.EMAIL;
    }
    
}


File: seyren-core/src/main/java/com/seyren/core/util/config/SeyrenConfig.java
/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.seyren.core.util.config;

import static org.apache.commons.lang.StringUtils.isNotEmpty;
import static org.apache.commons.lang.StringUtils.stripEnd;

import java.util.Arrays;
import java.util.List;

import javax.annotation.PostConstruct;
import javax.inject.Named;

import org.apache.velocity.app.Velocity;
import org.apache.velocity.runtime.RuntimeConstants;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.seyren.core.util.velocity.Slf4jLogChute;

@Named
public class SeyrenConfig {
    
    private static final String DEFAULT_BASE_URL = "http://localhost:8080/seyren";

    private final String baseUrl;
    private final String mongoUrl;
    private final String graphsEnable;
    private final String graphiteUrl;
    private final String graphiteUsername;
    private final String graphitePassword;
    private final String graphiteKeyStore;
    private final String graphiteKeyStorePassword;
    private final String graphiteTrustStore;
    private final String graphiteCarbonPickleEnable;
    private final String graphiteCarbonPicklePort;
    private final int graphiteConnectionRequestTimeout;
    private final int graphiteConnectTimeout;
    private final int graphiteSocketTimeout;
    private final String twilioUrl;
    private final String twilioAccountSid;
    private final String twilioAuthToken;
    private final String twilioPhoneNumber;
    private final String hipChatBaseUrl;
    private final String hipChatAuthToken;
    private final String hipChatUsername;
    private final String hubotUrl;
    private final String smtpFrom;
    private final String smtpUsername;
    private final String smtpPassword;
    private final String smtpHost;
    private final String smtpProtocol;
    private final Integer smtpPort;
    private final String flowdockExternalUsername;
    private final String flowdockTags;
    // Icon mapped check sate (AlertType) see http://apps.timwhitlock.info/emoji/tables/unicode
    // question, sunny, cloud, voltage exclamation should be: \u2753,\u2600,\u2601,\u26A1,\u2757
    private final String flowdockEmojis;
    private final String ircCatHost;
    private final String ircCatPort;
    private final String slackToken;
    private final String slackUsername;
    private final String slackIconUrl;
    private final String slackEmojis;
    private final String pushoverAppApiToken;
    private final String snmpHost;
    private final Integer snmpPort;
    private final String snmpCommunity;
    private final String snmpOID;
    private final String victorOpsRestAPIEndpoint;
    private final String emailTemplateFileName;
    private final int noOfThreads;
    private final String httpNotificationUrl;
    public SeyrenConfig() {
        
        // Base
        this.baseUrl = stripEnd(configOrDefault("SEYREN_URL", DEFAULT_BASE_URL), "/");
        this.mongoUrl = configOrDefault("MONGO_URL", "mongodb://localhost:27017/seyren");
        this.graphsEnable = configOrDefault("GRAPHS_ENABLE", "true");
        this.noOfThreads = Integer.parseInt(configOrDefault("SEYREN_THREADS", "8"));
        // Graphite
        this.graphiteUrl = stripEnd(configOrDefault("GRAPHITE_URL", "http://localhost:80"), "/");
        this.graphiteUsername = configOrDefault("GRAPHITE_USERNAME", "");
        this.graphitePassword = configOrDefault("GRAPHITE_PASSWORD", "");
        this.graphiteKeyStore = configOrDefault("GRAPHITE_KEYSTORE", "");
        this.graphiteKeyStorePassword = configOrDefault("GRAPHITE_KEYSTORE_PASSWORD", "");
        this.graphiteTrustStore = configOrDefault("GRAPHITE_TRUSTSTORE", "");
        this.graphiteCarbonPickleEnable = configOrDefault("GRAPHITE_CARBON_PICKLE_ENABLE", "false");
        this.graphiteCarbonPicklePort = configOrDefault("GRAPHITE_CARBON_PICKLE_PORT", "2004");
        this.graphiteConnectionRequestTimeout = Integer.parseInt(configOrDefault("GRAPHITE_CONNECTION_REQUEST_TIMEOUT", "0"));
        this.graphiteConnectTimeout = Integer.parseInt(configOrDefault("GRAPHITE_CONNECT_TIMEOUT", "0"));
        this.graphiteSocketTimeout = Integer.parseInt(configOrDefault("GRAPHITE_SOCKET_TIMEOUT", "0"));

        // HTTP

        this.httpNotificationUrl = configOrDefault("HTTP_NOTIFICATION_URL", "");

        // SMTP
        this.smtpFrom = configOrDefault(list("SMTP_FROM", "SEYREN_FROM_EMAIL"), "alert@seyren");
        this.smtpUsername = configOrDefault("SMTP_USERNAME", "");
        this.smtpPassword = configOrDefault("SMTP_PASSWORD", "");
        this.smtpHost = configOrDefault("SMTP_HOST", "localhost");
        this.smtpProtocol = configOrDefault("SMTP_PROTOCOL", "smtp");
        this.smtpPort = Integer.parseInt(configOrDefault("SMTP_PORT", "25"));
        
        // HipChat
        this.hipChatBaseUrl = configOrDefault(list("HIPCHAT_BASEURL", "HIPCHAT_BASE_URL"), "https://api.hipchat.com");
        this.hipChatAuthToken = configOrDefault(list("HIPCHAT_AUTHTOKEN", "HIPCHAT_AUTH_TOKEN"), "");
        this.hipChatUsername = configOrDefault(list("HIPCHAT_USERNAME", "HIPCHAT_USER_NAME"), "Seyren Alert");
        
        // PagerDuty

        // Twilio
        this.twilioUrl = configOrDefault("TWILIO_URL", "https://api.twilio.com/2010-04-01/Accounts");
        this.twilioAccountSid = configOrDefault("TWILIO_ACCOUNT_SID", "");
        this.twilioAuthToken = configOrDefault("TWILIO_AUTH_TOKEN", "");
        this.twilioPhoneNumber = configOrDefault("TWILIO_PHONE_NUMBER", "");
        
        // Hubot
        this.hubotUrl = configOrDefault(list("HUBOT_URL", "SEYREN_HUBOT_URL"), "");
        
        // Flowdock
        this.flowdockExternalUsername = configOrDefault("FLOWDOCK_EXTERNAL_USERNAME", "Seyren");
        this.flowdockTags = configOrDefault("FLOWDOCK_TAGS", "");
        this.flowdockEmojis = configOrDefault("FLOWDOCK_EMOJIS", "");

        // IrcCat
        this.ircCatHost = configOrDefault("IRCCAT_HOST", "localhost");
        this.ircCatPort = configOrDefault("IRCCAT_PORT", "12345");

        // Slack
        this.slackToken = configOrDefault("SLACK_TOKEN", "");
        this.slackUsername = configOrDefault("SLACK_USERNAME", "Seyren");
        this.slackIconUrl = configOrDefault("SLACK_ICON_URL", "");
        this.slackEmojis = configOrDefault("SLACK_EMOJIS", "");

        // PushOver
        this.pushoverAppApiToken = configOrDefault("PUSHOVER_APP_API_TOKEN", "");

        // SNMP
        this.snmpHost = configOrDefault("SNMP_HOST", "localhost");
        this.snmpPort = Integer.parseInt(configOrDefault("SNMP_PORT", "162"));
        this.snmpCommunity = configOrDefault("SNMP_COMMUNITY", "public");
        this.snmpOID = configOrDefault("SNMP_OID", "1.3.6.1.4.1.32473.1");

        //VictorOps
        this.victorOpsRestAPIEndpoint = configOrDefault("VICTOROPS_REST_ENDPOINT", "");

        // Template
        this.emailTemplateFileName = configOrDefault("TEMPLATE_EMAIL_FILE_PATH","com/seyren/core/service/notification/email-template.vm");
    }
    
    @PostConstruct
    public void init() {
        Velocity.setProperty(RuntimeConstants.RUNTIME_LOG_LOGSYSTEM, new Slf4jLogChute());
        Velocity.init();
    }
    
    public String getBaseUrl() {
        return baseUrl;
    }

    @JsonIgnore
    public boolean isBaseUrlSetToDefault() {
        return getBaseUrl().equals(DEFAULT_BASE_URL);
    }
    
    @JsonIgnore
    public String getMongoUrl() {
        return mongoUrl;
    }

    public boolean isGraphsEnabled() {
        return Boolean.valueOf(graphsEnable);
    }
    
    @JsonIgnore
    public String getTwilioUrl() {
        return twilioUrl;
    }

    @JsonIgnore
    public String getTwilioAccountSid() {
        return twilioAccountSid;
    }

    @JsonIgnore
    public String getTwilioAuthToken() {
        return twilioAuthToken;
    }
    
    @JsonIgnore
    public String getTwilioPhoneNumber() {
        return twilioPhoneNumber;
    }

    @JsonIgnore
    public String getHipChatBaseUrl() {
        return hipChatBaseUrl;
    }

    @JsonIgnore
    public String getHipChatAuthToken() {
        return hipChatAuthToken;
    }
    
    @JsonIgnore
    public String getHipChatUsername() {
        return hipChatUsername;
    }
    
    @JsonIgnore
    public String getHubotUrl() {
        return hubotUrl;
    }
    
    @JsonIgnore
    public String getFlowdockExternalUsername() {
        return flowdockExternalUsername;
    }
    
    @JsonIgnore
    public String getFlowdockTags() {
        return flowdockTags;
    }
    
    @JsonIgnore
    public String getFlowdockEmojis() {
        return flowdockEmojis;
    }

    @JsonIgnore
    public String getIrcCatHost() {
        return this.ircCatHost;
    }

    @JsonIgnore
    public int getIrcCatPort() {
        return Integer.valueOf(this.ircCatPort);
    }

    @JsonIgnore
    public String getPushoverAppApiToken() {
        return this.pushoverAppApiToken;
    }

    @JsonIgnore
    public String getSmtpFrom() {
        return smtpFrom;
    }
    
    @JsonIgnore
    public String getSmtpUsername() {
        return smtpUsername;
    }
    
    @JsonIgnore
    public String getSmtpPassword() {
        return smtpPassword;
    }
    
    @JsonIgnore
    public String getSmtpHost() {
        return smtpHost;
    }
    
    @JsonIgnore
    public String getSmtpProtocol() {
        return smtpProtocol;
    }
    
    @JsonIgnore
    public Integer getSmtpPort() {
        return smtpPort;
    }

    @JsonIgnore
    public String getSnmpHost() {
        return snmpHost;
    }
    
    @JsonIgnore
    public Integer getSnmpPort() {
        return snmpPort;
    }
    
    @JsonIgnore
    public String getSnmpCommunity() {
        return snmpCommunity;
    }
    
    @JsonIgnore
    public String getSnmpOID() {
        return snmpOID;
    }
    
    @JsonIgnore
    public String getGraphiteUrl() {
        return graphiteUrl;
    }
    
    @JsonIgnore
    public String getGraphiteUsername() {
        return graphiteUsername;
    }
    
    @JsonIgnore
    public String getGraphitePassword() {
        return graphitePassword;
    }
    
    @JsonIgnore
    public String getGraphiteScheme() {
        return splitBaseUrl(graphiteUrl)[0];
    }
    
    @JsonIgnore
    public int getGraphiteSSLPort() {
        return Integer.valueOf(splitBaseUrl(graphiteUrl)[1]);
    }
    
    @JsonIgnore
    public String getGraphiteHost() {
        return splitBaseUrl(graphiteUrl)[2];
    }
    
    @JsonIgnore
    public String getGraphitePath() {
        return splitBaseUrl(graphiteUrl)[3];
    }
    
    @JsonIgnore
    public String getGraphiteKeyStore() {
        return graphiteKeyStore;
    }
    
    @JsonIgnore
    public String getGraphiteKeyStorePassword() {
        return graphiteKeyStorePassword;
    }

    @JsonIgnore
    public String getGraphiteTrustStore() {
        return graphiteTrustStore;
    }

    @JsonIgnore
    public int getGraphiteCarbonPicklePort() {
        return Integer.valueOf(graphiteCarbonPicklePort);
    }

    @JsonProperty("graphiteCarbonPickleEnabled")
    public boolean getGraphiteCarbonPickleEnable() {
        return Boolean.valueOf(graphiteCarbonPickleEnable);
    }
    
    @JsonIgnore
    public int getGraphiteConnectionRequestTimeout() {
        return graphiteConnectionRequestTimeout;
    }
    
    @JsonIgnore
    public int getGraphiteConnectTimeout() {
        return graphiteConnectTimeout;
    }
    
    @JsonIgnore
    public int getGraphiteSocketTimeout() {
        return graphiteSocketTimeout;
    }

    @JsonIgnore
    public String getSlackToken() {
      return slackToken;
    }

    @JsonIgnore
    public String getSlackUsername() {
      return slackUsername;
    }

    @JsonIgnore
    public String getSlackIconUrl() {
      return slackIconUrl;
    }

    @JsonIgnore
    public String getSlackEmojis() {
      return slackEmojis;
    }

    @JsonIgnore
    public int getNoOfThreads() {
        return noOfThreads;
    }

    @JsonIgnore
    public String getHttpNotificationUrl() {
        return httpNotificationUrl;
    }

    @JsonIgnore
    public String getEmailTemplateFileName() { return emailTemplateFileName; }

    @JsonIgnore
    public String getVictorOpsRestEndpoint() {
        return victorOpsRestAPIEndpoint;
    }


  private static String configOrDefault(String propertyName, String defaultValue) {
        return configOrDefault(list(propertyName), defaultValue);
    }
    
    private static String configOrDefault(List<String> propertyNames, String defaultValue) {
        
        for (String propertyName : propertyNames) {
            
            String value = System.getProperty(propertyName);
            if (isNotEmpty(value)) {
                return value;
            }
            
            value = System.getenv(propertyName);
            if (isNotEmpty(value)) {
                return value;
            }
        }
        
        return defaultValue;
    }
    
    private static List<String> list(String... propertyNames) {
        return Arrays.asList(propertyNames);
    }
    
    private static String[] splitBaseUrl(String baseUrl) {
        String[] baseParts = new String[4];
        
        if (baseUrl.toString().contains("://")) {
            baseParts[0] = baseUrl.toString().split("://")[0];
            baseUrl = baseUrl.toString().split("://")[1];
        } else {
            baseParts[0] = "http";
        }
        
        if (baseUrl.contains(":")) {
            baseParts[1] = baseUrl.split(":")[1];
        } else {
            baseParts[1] = "443";
        }
        
        if (baseUrl.contains("/")) {
            baseParts[2] = baseUrl.split("/")[0];
            baseParts[3] = "/" + baseUrl.split("/", 2)[1];
        } else {
            baseParts[2] = baseUrl;
            baseParts[3] = "";
        }
        
        return baseParts;
    }
}


File: seyren-core/src/main/java/com/seyren/core/util/email/EmailHelper.java
/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.seyren.core.util.email;

import java.util.List;

import com.seyren.core.domain.Alert;
import com.seyren.core.domain.Check;
import com.seyren.core.domain.Subscription;

public interface EmailHelper {
    
    String createSubject(Check check);
    
    String createBody(Check check, Subscription subscription, List<Alert> alerts);
    
}


File: seyren-core/src/main/java/com/seyren/core/util/velocity/VelocityEmailHelper.java
/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.seyren.core.util.velocity;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.StringWriter;
import java.net.URL;
import java.util.List;

import javax.inject.Inject;
import javax.inject.Named;

import org.apache.commons.io.IOUtils;
import org.apache.velocity.VelocityContext;
import org.apache.velocity.app.Velocity;

import com.seyren.core.domain.Alert;
import com.seyren.core.domain.Check;
import com.seyren.core.domain.Subscription;
import com.seyren.core.util.config.SeyrenConfig;
import com.seyren.core.util.email.EmailHelper;

@Named
public class VelocityEmailHelper implements EmailHelper {

    // Will first attempt to load from classpath then fall back to loading from the filesystem.
    private final String TEMPLATE_FILE_NAME;
    private final String TEMPLATE_CONTENT;
    
    private final SeyrenConfig seyrenConfig;

    /**
     * Loads content of configurable templated email message at creation time.
     *
     * @param seyrenConfig Used for both email template file name and the seyren URL.
     */
    @Inject
    public VelocityEmailHelper(SeyrenConfig seyrenConfig) {
        this.seyrenConfig = seyrenConfig;
        TEMPLATE_FILE_NAME = seyrenConfig.getEmailTemplateFileName();
        TEMPLATE_CONTENT = getTemplateAsString();
    }
    
    public String createSubject(Check check) {
        return "Seyren alert: " + check.getName();
    }
    
    @Override
    public String createBody(Check check, Subscription subscription, List<Alert> alerts) {
        VelocityContext context = createVelocityContext(check, subscription, alerts);
        StringWriter stringWriter = new StringWriter();
        Velocity.evaluate(context, stringWriter, "EmailNotificationService", TEMPLATE_CONTENT);
        return stringWriter.toString();
    }
    
    private VelocityContext createVelocityContext(Check check, Subscription subscription, List<Alert> alerts) {
        VelocityContext result = new VelocityContext();
        result.put("CHECK", check);
        result.put("ALERTS", alerts);
        result.put("SEYREN_URL", seyrenConfig.getBaseUrl());
        return result;
    }
    
    private String getTemplateAsString() {
        try {
            // Handle the template filename as either a class path resource or an absolute path to the filesystem.
            InputStream inputStream = Thread.currentThread().getContextClassLoader().getResourceAsStream(TEMPLATE_FILE_NAME);
            if (inputStream == null) {
                inputStream = new FileInputStream(TEMPLATE_FILE_NAME);
            }
            return IOUtils.toString(inputStream);
        } catch (IOException e) {
            throw new RuntimeException("Template file could not be found on classpath at " + TEMPLATE_FILE_NAME);
        }
    }
    
}


File: seyren-core/src/test/java/com/seyren/core/util/config/SeyrenConfigTest.java
/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.seyren.core.util.config;

import static org.hamcrest.MatcherAssert.*;
import static org.hamcrest.Matchers.*;

import org.junit.Before;
import org.junit.Test;

import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.is;

public class SeyrenConfigTest {
    
    private SeyrenConfig config;
    
    @Before
    public void before() {
        config = new SeyrenConfig();
    }
    
    @Test
    public void defaultBaseUrlIsCorrect() {
        if (config.isBaseUrlSetToDefault()) {
            assertThat(config.getBaseUrl(), is("http://localhost:8080/seyren"));
        }
    }
    
    @Test
    public void defaultMongoUrlIsCorrect() {
        assertThat(config.getMongoUrl(), is("mongodb://localhost:27017/seyren"));
    }
    
    @Test
    public void defaultGraphiteUrlIsCorrect() {
        assertThat(config.getGraphiteUrl(), is("http://localhost:80"));
    }

    @Test
    public void defaultGraphsEnable() {
      assertThat(config.isGraphsEnabled(), is(true));
    }

    @Test
    public void defaultGraphiteUsernameIsCorrect() {
        assertThat(config.getGraphiteUsername(), is(""));
    }
    
    @Test
    public void defaultGraphitePasswordIsCorrect() {
        assertThat(config.getGraphitePassword(), is(""));
    }
    
    @Test
    public void defaultGraphiteSchemeIsCorrect() {
        assertThat(config.getGraphiteScheme(), is("http"));
    }
    
    @Test
    public void defaultGraphiteHostIsCorrect() {
        assertThat(config.getGraphiteHost(), is("localhost:80"));
    }
    
    @Test
    public void defaultGraphitePathIsCorrect() {
        assertThat(config.getGraphitePath(), is(""));
    }
    
    @Test
    public void defaultGraphiteKeyStoreIsCorrect() {
        assertThat(config.getGraphiteKeyStore(), is(""));
    }
    
    @Test
    public void defaultGraphiteKeyStorePasswordIsCorrect() {
        assertThat(config.getGraphiteKeyStorePassword(), is(""));
    }
    
    @Test
    public void defaultGraphiteTrustStoreIsCorrect() {
        assertThat(config.getGraphiteTrustStore(), is(""));
    }
    
    @Test
    public void defaultSmtpFromIsCorrect() {
        assertThat(config.getSmtpFrom(), is("alert@seyren"));
    }
    
    @Test
    public void defaultSmtpUsernameIsCorrect() {
        assertThat(config.getSmtpUsername(), is(""));
    }
    
    @Test
    public void defaultSmtpPasswordIsCorrect() {
        assertThat(config.getSmtpPassword(), is(""));
    }
    
    @Test
    public void defaultSmtpHostIsCorrect() {
        assertThat(config.getSmtpHost(), is("localhost"));
    }
    
    @Test
    public void defaultSmtpProtocolIsCorrect() {
        assertThat(config.getSmtpProtocol(), is("smtp"));
    }
    
    @Test
    public void defaultSmtpPortIsCorrect() {
        assertThat(config.getSmtpPort(), is(25));
    }
    
    @Test
    public void defaultHipChatAuthTokenIsCorrect() {
        assertThat(config.getHipChatAuthToken(), is(""));
    }
    
    @Test
    public void defaultHipChatUsernameIsCorrect() {
        assertThat(config.getHipChatUsername(), is("Seyren Alert"));
    }
    
    @Test
    public void defaultHubotUrlIsCorrect() {
        assertThat(config.getHubotUrl(), is(""));
    }
    
    @Test
    public void defaultFlowdockExternalUsernameIsCorrect() {
        assertThat(config.getFlowdockExternalUsername(), is("Seyren"));
    }
    
    @Test
    public void defaultFlowdockTagsIsCorrect() {
        assertThat(config.getFlowdockTags(), is(""));
    }
    
    @Test
    public void defaultFlowdockEmojisIsCorrect() {
        assertThat(config.getFlowdockEmojis(), is(""));
    }

    @Test
    public void defaultEmailTemplateFileIsCorrect() {
        assertThat(config.getEmailTemplateFileName(), is("com/seyren/core/service/notification/email-template.vm"));
    }

    @Test
    public void defaultNumOfThreadsIsCorrect() {
        assertThat(config.getNoOfThreads(), is(8));
    }
    
}


File: seyren-core/src/test/java/com/seyren/core/util/velocity/VelocityEmailHelperTest.java
/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.seyren.core.util.velocity;

import static org.hamcrest.MatcherAssert.*;
import static org.hamcrest.Matchers.*;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;

import org.joda.time.DateTime;
import org.junit.Before;
import org.junit.Test;

import com.seyren.core.domain.Alert;
import com.seyren.core.domain.AlertType;
import com.seyren.core.domain.Check;
import com.seyren.core.domain.Subscription;
import com.seyren.core.domain.SubscriptionType;
import com.seyren.core.util.config.SeyrenConfig;
import com.seyren.core.util.email.EmailHelper;

public class VelocityEmailHelperTest {
    
    private EmailHelper emailHelper;
    
    @Before
    public void before() {
        emailHelper = new VelocityEmailHelper(new SeyrenConfig());
    }
    
    @Test
    public void subjectIsCorrect() {
        
        Check check = new Check()
                .withId("123")
                .withEnabled(true)
                .withName("test-check")
                .withState(AlertType.ERROR);
        
        String subject = emailHelper.createSubject(check);
        
        assertThat(subject, is("Seyren alert: test-check"));
        
    }
    
    @Test
    public void bodyContainsRightSortsOfThings() {
        
        Check check = new Check()
                .withId("123")
                .withEnabled(true)
                .withName("test-check")
                .withDescription("Some great description")
                .withWarn(new BigDecimal("2.0"))
                .withError(new BigDecimal("3.0"))
                .withState(AlertType.ERROR);
        Subscription subscription = new Subscription()
                .withEnabled(true)
                .withType(SubscriptionType.EMAIL)
                .withTarget("some@email.com");
        Alert alert = new Alert()
                .withTarget("some.value")
                .withValue(new BigDecimal("4.0"))
                .withTimestamp(new DateTime())
                .withFromType(AlertType.OK)
                .withToType(AlertType.ERROR);
        List<Alert> alerts = Arrays.asList(alert);
        
        String body = emailHelper.createBody(check, subscription, alerts);
        
        assertThat(body, containsString("test-check"));
        assertThat(body, containsString("Some great description"));
        assertThat(body, containsString("some.value"));
        assertThat(body, containsString("2.0"));
        assertThat(body, containsString("3.0"));
        assertThat(body, containsString("4.0"));
        
    }
    
    @Test
    public void descriptionIsNotIncludedIfEmpty() {
        
        Check check = new Check()
                .withId("123")
                .withEnabled(true)
                .withName("test-check")
                .withDescription("")
                .withWarn(new BigDecimal("2.0"))
                .withError(new BigDecimal("3.0"))
                .withState(AlertType.ERROR);
        Subscription subscription = new Subscription()
                .withEnabled(true)
                .withType(SubscriptionType.EMAIL)
                .withTarget("some@email.com");
        Alert alert = new Alert()
                .withTarget("some.value")
                .withValue(new BigDecimal("4.0"))
                .withTimestamp(new DateTime())
                .withFromType(AlertType.OK)
                .withToType(AlertType.ERROR);
        List<Alert> alerts = Arrays.asList(alert);
        
        String body = emailHelper.createBody(check, subscription, alerts);
        
        assertThat(body, not(containsString("<p></p>")));
        
    }
    
    @Test
    public void bodyDoesNotContainScientificNotationOfNumber() {
        
        Check check = new Check()
                .withId("123")
                .withEnabled(true)
                .withName("test-check")
                .withWarn(new BigDecimal("2.0"))
                .withError(new BigDecimal("3.0"))
                .withState(AlertType.ERROR);
        Subscription subscription = new Subscription()
                .withEnabled(true)
                .withType(SubscriptionType.EMAIL)
                .withTarget("some@email.com");
        Alert alert = new Alert()
                .withTarget("some.value")
                .withValue(new BigDecimal("138362880"))
                .withTimestamp(new DateTime())
                .withFromType(AlertType.OK)
                .withToType(AlertType.ERROR);
        List<Alert> alerts = Arrays.asList(alert);
        
        String body = emailHelper.createBody(check, subscription, alerts);
        
        assertThat(body, containsString("138362880"));
        
    }

    @Test
    public void templateLocationShouldBeConfigurable() {
        SeyrenConfig mockConfiguration = mock(SeyrenConfig.class);
        when(mockConfiguration.getEmailTemplateFileName()).thenReturn("test-email-template.vm");
        EmailHelper emailHelper = new VelocityEmailHelper(mockConfiguration);
        String body = emailHelper.createBody(null, null, null);
        assertThat(body, containsString("Test content."));
    }
}
