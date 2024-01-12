Refactoring Types: ['Pull Up Method']
thub/dreamhead/moco/internal/ActualHttpServer.java
package com.github.dreamhead.moco.internal;

import com.github.dreamhead.moco.*;
import com.github.dreamhead.moco.dumper.HttpRequestDumper;
import com.github.dreamhead.moco.dumper.HttpResponseDumper;
import com.github.dreamhead.moco.monitor.QuietMonitor;
import com.github.dreamhead.moco.monitor.Slf4jMonitor;
import com.github.dreamhead.moco.setting.HttpSetting;
import com.google.common.base.Optional;
import com.google.common.net.HttpHeaders;
import io.netty.handler.codec.http.HttpResponseStatus;

import static com.github.dreamhead.moco.Moco.header;
import static com.github.dreamhead.moco.Moco.status;
import static com.github.dreamhead.moco.util.Configs.configItem;
import static com.github.dreamhead.moco.util.Preconditions.checkNotNullOrEmpty;
import static com.google.common.base.Optional.absent;
import static com.google.common.base.Optional.of;

public class ActualHttpServer extends HttpConfiguration {
    protected final Optional<HttpsCertificate> certificate;

    protected ActualHttpServer(final Optional<Integer> port, final Optional<HttpsCertificate> certificate, final MocoMonitor monitor, final MocoConfig... configs) {
        super(port, monitor, configs);
        this.certificate = certificate;
    }

    public boolean isSecure() {
        return certificate.isPresent();
    }

    public Optional<HttpsCertificate> getCertificate() {
        return certificate;
    }

    public HttpServer mergeHttpServer(final ActualHttpServer thatServer) {
        ActualHttpServer newServer = newBaseServer(newServerCertificate(thatServer.certificate));
        newServer.addSettings(this.getSettings());
        newServer.addSettings(thatServer.getSettings());

        newServer.anySetting(configItem(this.matcher, this.configs), configItem(this.handler, this.configs));
        newServer.anySetting(configItem(thatServer.matcher, thatServer.configs), configItem(thatServer.handler, thatServer.configs));

        newServer.addEvents(this.eventTriggers);
        newServer.addEvents(thatServer.eventTriggers);

        return newServer;
    }

    private Optional<HttpsCertificate> newServerCertificate(final Optional<HttpsCertificate> certificate) {
        if (this.isSecure()) {
            return this.certificate;
        }

        if (certificate.isPresent()) {
            return certificate;
        }

        return absent();
    }

    private ActualHttpServer newBaseServer(final Optional<HttpsCertificate> certificate) {
        if (certificate.isPresent()) {
            return createHttpsLogServer(getPort(), certificate.get());
        }

        return createLogServer(getPort());
    }

    public static ActualHttpServer createHttpServerWithMonitor(final Optional<Integer> port, final MocoMonitor monitor, final MocoConfig... configs) {
        return new ActualHttpServer(port, Optional.<HttpsCertificate>absent(), monitor, configs);
    }

    public static ActualHttpServer createLogServer(final Optional<Integer> port, final MocoConfig... configs) {
        return createHttpServerWithMonitor(port, new Slf4jMonitor(new HttpRequestDumper(), new HttpResponseDumper()), configs);
    }

    public static ActualHttpServer createQuietServer(final Optional<Integer> port, final MocoConfig... configs) {
        return createHttpServerWithMonitor(port, new QuietMonitor(), configs);
    }

    public static ActualHttpServer createHttpsServerWithMonitor(final Optional<Integer> port, final HttpsCertificate certificate, MocoMonitor monitor, MocoConfig... configs) {
        return new ActualHttpServer(port, of(certificate), monitor, configs);
    }

    public static ActualHttpServer createHttpsLogServer(final Optional<Integer> port, final HttpsCertificate certificate, final MocoConfig... configs) {
        return createHttpsServerWithMonitor(port, certificate, new Slf4jMonitor(new HttpRequestDumper(), new HttpResponseDumper()), configs);
    }

    public static ActualHttpServer createHttpsQuietServer(final Optional<Integer> port, final HttpsCertificate certificate, final MocoConfig... configs) {
        return ActualHttpServer.createHttpsServerWithMonitor(port, certificate, new QuietMonitor(), configs);
    }

    @Override
    public HttpResponseSetting redirectTo(final String url) {
        return this.response(status(HttpResponseStatus.FOUND.code()), header(HttpHeaders.LOCATION, checkNotNullOrEmpty(url, "URL should not be null")));
    }

    @Override
    protected HttpResponseSetting onRequestAttached(final RequestMatcher matcher) {
        HttpSetting baseSetting = new HttpSetting(matcher);
        addSetting(baseSetting);
        return baseSetting;
    }

    @Override
    protected HttpSetting newSetting(final RequestMatcher matcher) {
        return new HttpSetting(matcher);
    }
}


File: moco-core/src/main/java/com/github/dreamhead/moco/internal/HttpConfiguration.java
package com.github.dreamhead.moco.internal;

import com.github.dreamhead.moco.*;
import com.github.dreamhead.moco.handler.failover.Failover;
import com.github.dreamhead.moco.handler.proxy.ProxyConfig;
import com.github.dreamhead.moco.mount.MountHandler;
import com.github.dreamhead.moco.mount.MountMatcher;
import com.github.dreamhead.moco.mount.MountPredicate;
import com.github.dreamhead.moco.mount.MountTo;
import com.google.common.base.Optional;
import io.netty.handler.codec.http.HttpMethod;

import java.io.File;

import static com.github.dreamhead.moco.Moco.*;
import static com.github.dreamhead.moco.util.Preconditions.checkNotNullOrEmpty;
import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.collect.ImmutableList.copyOf;

public abstract class HttpConfiguration extends BaseActualServer<HttpResponseSetting> implements HttpsServer {
    protected HttpConfiguration(final Optional<Integer> port, final MocoMonitor monitor, final MocoConfig[] configs) {
        super(port, monitor, configs);
    }

    @Override
    public HttpResponseSetting get(final RequestMatcher matcher) {
        return requestByHttpMethod(HttpMethod.GET, checkNotNull(matcher, "Matcher should not be null"));
    }

    @Override
    public HttpResponseSetting post(final RequestMatcher matcher) {
        return requestByHttpMethod(HttpMethod.POST, checkNotNull(matcher, "Matcher should not be null"));
    }

    @Override
    public HttpResponseSetting put(final RequestMatcher matcher) {
        return requestByHttpMethod(HttpMethod.PUT, checkNotNull(matcher, "Matcher should not be null"));
    }

    @Override
    public HttpResponseSetting delete(final RequestMatcher matcher) {
        return requestByHttpMethod(HttpMethod.DELETE, checkNotNull(matcher, "Matcher should not be null"));
    }

    @Override
    public HttpResponseSetting mount(final String dir, final MountTo target, final MountPredicate... predicates) {
        File mountedDir = new File(checkNotNullOrEmpty(dir, "Directory should not be null"));
        checkNotNull(target, "Target should not be null");
        return this.request(new MountMatcher(mountedDir, target, copyOf(predicates))).response(new MountHandler(mountedDir, target));
    }

    private HttpResponseSetting requestByHttpMethod(final HttpMethod method, final RequestMatcher matcher) {
        return request(and(by(method(method.name())), matcher));
    }

    @Override
    public HttpResponseSetting proxy(final ProxyConfig config) {
        return proxy(checkNotNull(config, "Proxy config should not be null"), Failover.DEFAULT_FAILOVER);
    }

    @Override
    public HttpResponseSetting proxy(final ProxyConfig proxyConfig, final Failover failover) {
        ProxyConfig config = checkNotNull(proxyConfig, "Proxy config should not be null");
        this.request(InternalApis.context(config.localBase())).response(Moco.proxy(config, checkNotNull(failover, "Failover should not be null")));
        return this;
    }
}
