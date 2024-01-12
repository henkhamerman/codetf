Refactoring Types: ['Extract Method']
m/spotify/helios/common/JobValidator.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.common;

import com.google.common.base.Joiner;
import com.google.common.collect.Sets;

import com.spotify.helios.common.descriptors.ExecHealthCheck;
import com.spotify.helios.common.descriptors.HealthCheck;
import com.spotify.helios.common.descriptors.HttpHealthCheck;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.PortMapping;
import com.spotify.helios.common.descriptors.ServiceEndpoint;
import com.spotify.helios.common.descriptors.ServicePorts;
import com.spotify.helios.common.descriptors.TcpHealthCheck;

import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

import static com.google.common.base.Strings.isNullOrEmpty;
import static java.lang.String.format;
import static java.util.regex.Pattern.compile;

public class JobValidator {

  public static final Pattern NAME_VERSION_PATTERN = Pattern.compile("[0-9a-zA-Z-_.]+");

  public static final Pattern DOMAIN_PATTERN =
      Pattern.compile("^(?:(?:[a-zA-Z0-9]|(?:[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9]))" +
                      "(\\.(?:[a-zA-Z0-9]|(?:[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])))*)\\.?$");

  public static final Pattern IPV4_PATTERN =
      Pattern.compile("^(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})$");

  public static final Pattern NAMESPACE_PATTERN = Pattern.compile("^([a-z0-9_]{4,30})$");
  public static final Pattern REPO_PATTERN = Pattern.compile("^([a-z0-9-_.]+)$");
  public static final Pattern DIGIT_PERIOD = Pattern.compile("^[0-9.]+$");

  public static final Pattern PORT_MAPPING_PROTO_PATTERN = compile("(tcp|udp)");
  public static final Pattern PORT_MAPPING_NAME_PATTERN = compile("\\S+");
  public static final Pattern REGISTRATION_NAME_PATTERN = compile("[_\\-\\w]+");

  public Set<String> validate(final Job job) {
    final Set<String> errors = Sets.newHashSet();

    errors.addAll(validateJobId(job));
    errors.addAll(validateJobImage(job.getImage()));

    // Check that there's not external port collision
    final Set<Integer> externalPorts = Sets.newHashSet();
    for (final PortMapping mapping : job.getPorts().values()) {
      Integer externalMappedPort = mapping.getExternalPort();
      if (externalPorts.contains(externalMappedPort) && externalMappedPort != null) {
        errors.add(format("Duplicate external port mapping: %s", externalMappedPort));
      }
      externalPorts.add(externalMappedPort);
    }

    // Verify port mappings
    for (final Map.Entry<String, PortMapping> entry : job.getPorts().entrySet()) {
      final String name = entry.getKey();
      final PortMapping mapping = entry.getValue();
      if (!PORT_MAPPING_PROTO_PATTERN.matcher(mapping.getProtocol()).matches()) {
        errors.add(format("Invalid port mapping protocol: %s", mapping.getProtocol()));
      }
      if (!legalPort(mapping.getInternalPort())) {
        errors.add(format("Invalid internal port: %d", mapping.getInternalPort()));
      }
      if (mapping.getExternalPort() != null && !legalPort(mapping.getExternalPort())) {
        errors.add(format("Invalid external port: %d", mapping.getExternalPort()));
      }
      if (!PORT_MAPPING_NAME_PATTERN.matcher(name).matches()) {
        errors.add(format("Invalid port mapping endpoint name: %s", name));
      }
    }

    // Verify service registrations
    for (final ServiceEndpoint registration : job.getRegistration().keySet()) {
      final ServicePorts servicePorts = job.getRegistration().get(registration);
      for (final String portName : servicePorts.getPorts().keySet()) {
        if (!job.getPorts().containsKey(portName)) {
          errors.add(format("Service registration refers to missing port mapping: %s=%s",
                            registration, portName));
        }
        if (!REGISTRATION_NAME_PATTERN.matcher(registration.getName()).matches()) {
          errors.add(format("Invalid service registration name: %s", registration.getName()));
        }
      }
    }

    // Validate volumes
    for (Map.Entry<String, String> entry : job.getVolumes().entrySet()) {
      final String path = entry.getKey();
      final String source = entry.getValue();
      if (!path.startsWith("/")) {
        errors.add("Volume path is not absolute: " + path);
        continue;
      }
      if (!isNullOrEmpty(source) && !source.startsWith("/")) {
        errors.add("Volume source is not absolute: " + source);
        continue;
      }
      final String[] parts = path.split(":", 3);
      if (path.isEmpty() || path.equals("/") ||
          parts.length > 2 ||
          (parts.length > 1 && parts[1].isEmpty())) {
        errors.add(format("Invalid volume path: %s", path));
      }
    }

    // Validate Expiry
    final Date expiry = job.getExpires();
    if (expiry != null && expiry.before(new Date())) {
      errors.add("Job expires in the past");
    }

    errors.addAll(validateJobHealthCheck(job));

    return errors;
  }

  /**
   * Validate the Job's image by checking it's not null or empty and has the right format.
   * @param image The image String
   * @return A set of error Strings
   */
  private Set<String> validateJobImage(final String image) {
    final Set<String> errors = Sets.newHashSet();

    if (image == null) {
      errors.add("Image was not specified.");
    } else {
      // Validate image name
      validateImageReference(image, errors);
    }

    return errors;
  }

  /**
   * Validate the Job's JobId by checking name, version, and hash are
   * not null or empty, don't contain invalid characters.
   * @param job The Job to check.
   * @return A set of error Strings
   */
  private Set<String> validateJobId(final Job job) {
    final Set<String> errors = Sets.newHashSet();
    final JobId jobId = job.getId();

    if (jobId == null) {
      errors.add("Job id was not specified.");
      return errors;
    }

    final String jobIdVersion = jobId.getVersion();
    final String jobIdHash = jobId.getHash();
    final JobId recomputedId = job.toBuilder().build().getId();


    errors.addAll(validateJobName(jobId, recomputedId));
    errors.addAll(validateJobVersion(jobIdVersion, recomputedId));
    errors.addAll(validateJobHash(jobIdHash, recomputedId));

    return errors;
  }

  private Set<String> validateJobName(final JobId jobId, final JobId recomputedId) {
    final Set<String> errors = Sets.newHashSet();

    final String jobIdName = jobId.getName();
    if (jobIdName == null || jobIdName.isEmpty()) {
      errors.add("Job name was not specified.");
      return errors;
    }

    // Check that the job name contains only allowed characters
    if (!NAME_VERSION_PATTERN.matcher(jobIdName).matches()) {
      errors.add(format("Job name may only contain [0-9a-zA-Z-_.] in job name [%s].",
        recomputedId.getName()));
    }

    // Check that the job id is correct
    if (!recomputedId.getName().equals(jobIdName)) {
      errors.add(format("Id name mismatch: %s != %s", jobIdName, recomputedId.getName()));
    }

    return errors;
  }

  private Set<String> validateJobVersion(final String jobIdVersion, final JobId recomputedId) {
    final Set<String> errors = Sets.newHashSet();

    if (jobIdVersion == null || jobIdVersion.isEmpty()) {
      errors.add(format("Job version was not specified in job id [%s].", recomputedId));
      return errors;
    }

    if (!NAME_VERSION_PATTERN.matcher(jobIdVersion).matches()) {
      // Check that the job version contains only allowed characters
      errors.add(format("Job version may only contain [0-9a-zA-Z-_.] in job version [%s].",
          recomputedId.getVersion()));
    }

    // Check that the job version is correct
    if (!recomputedId.getVersion().equals(jobIdVersion)) {
      errors.add(format("Id version mismatch: %s != %s", jobIdVersion, recomputedId.getVersion()));
    }

    return errors;
  }

  private Set<String> validateJobHash(final String jobIdHash, final JobId recomputedId) {
    final Set<String> errors = Sets.newHashSet();

    if (jobIdHash == null || jobIdHash.isEmpty()) {
      errors.add(format("Job hash was not specified in job id [%s].", recomputedId));
      return errors;
    }

    if (jobIdHash.indexOf(':') != -1) {
      // TODO (dxia) Are hashes allowed to have chars not in NAME_VERSION_PATTERN?
      errors.add(format("Job hash contains colon in job id [%s].", recomputedId));
    }

    // Check that the job hash is correct
    if (!recomputedId.getHash().equals(jobIdHash)) {
      errors.add(format("Id hash mismatch: %s != %s", jobIdHash, recomputedId.getHash()));
    }

    return errors;
  }

  @SuppressWarnings("ConstantConditions")
  private boolean validateImageReference(final String imageRef, final Collection<String> errors) {
    boolean valid = true;

    final String repo;
    final String tag;

    final int lastColon = imageRef.lastIndexOf(':');
    if (lastColon != -1 && !(tag = imageRef.substring(lastColon + 1)).contains("/")) {
      repo = imageRef.substring(0, lastColon);
      valid &= validateTag(tag, errors);
    } else {
      repo = imageRef;
    }

    final String invalidRepoName = "Invalid repository name (ex: \"registry.domain.tld/myrepos\")";

    if (repo.contains("://")) {
      // It cannot contain a scheme!
      errors.add(invalidRepoName);
      return false;
    }

    final String[] nameParts = repo.split("/", 2);
    if (!nameParts[0].contains(".") &&
        !nameParts[0].contains(":") &&
        !nameParts[0].equals("localhost")) {
      // This is a Docker Index repos (ex: samalba/hipache or ubuntu)
      return validateRepositoryName(repo, errors);
    }

    if (nameParts.length < 2) {
      // There is a dot in repos name (and no registry address)
      // Is it a Registry address without repos name?
      errors.add(invalidRepoName);
      return false;
    }

    final String endpoint = nameParts[0];
    final String reposName = nameParts[1];
    valid &= validateEndpoint(endpoint, errors);
    valid &= validateRepositoryName(reposName, errors);
    return valid;
  }

  private boolean validateTag(final String tag, final Collection<String> errors) {
    boolean valid = true;
    if (tag.isEmpty()) {
      errors.add("Tag cannot be empty");
      valid = false;
    }
    if (tag.contains("/") || tag.contains(":")) {
      errors.add(format("Illegal tag: \"%s\"", tag));
      valid = false;
    }
    return valid;
  }

  private boolean validateEndpoint(final String endpoint, final Collection<String> errors) {
    final String[] parts = endpoint.split(":", 2);
    if (!validateAddress(parts[0], errors)) {
      return false;
    }
    if (parts.length > 1) {
      final int port;
      try {
        port = Integer.valueOf(parts[1]);
      } catch (NumberFormatException e) {
        errors.add(format("Invalid port in endpoint: \"%s\"", endpoint));
        return false;
      }
      if (port < 0 || port > 65535) {
        errors.add(format("Invalid port in endpoint: \"%s\"", endpoint));
        return false;
      }
    }
    return true;
  }

  private boolean validateAddress(final String address, final Collection<String> errors) {
    if (IPV4_PATTERN.matcher(address).matches()) {
      return true;
    } else if (!DOMAIN_PATTERN.matcher(address).matches() || DIGIT_PERIOD.matcher(address).find()) {
      errors.add(format("Invalid domain name: \"%s\"", address));
      return false;
    }
    return true;
  }

  private boolean validateRepositoryName(final String repositoryName,
                                         final Collection<String> errors) {
    boolean valid = true;
    String repo;
    String name;
    final String[] nameParts = repositoryName.split("/", 2);
    if (nameParts.length < 2) {
      repo = "library";
      name = nameParts[0];
    } else {
      repo = nameParts[0];
      name = nameParts[1];
    }
    if (!NAMESPACE_PATTERN.matcher(repo).matches()) {
      errors.add(
          format("Invalid namespace name (%s), only [a-z0-9_] are allowed, size between 4 and 30",
                 repo));
      valid = false;
    }
    if (!REPO_PATTERN.matcher(name).matches()) {
      errors.add(format("Invalid repository name (%s), only [a-z0-9-_.] are allowed", name));
      valid = false;
    }
    return valid;
  }

  /**
   * Validate the Job's health check.
   * @param job The Job to check.
   * @return A set of error Strings
   */
  private Set<String> validateJobHealthCheck(final Job job) {
    final HealthCheck healthCheck = job.getHealthCheck();

    if (healthCheck == null) {
      return Collections.emptySet();
    }

    final Set<String> errors = Sets.newHashSet();

    if (healthCheck instanceof ExecHealthCheck) {
      final List<String> command = ((ExecHealthCheck) healthCheck).getCommand();
      if (command == null || command.isEmpty()) {
        errors.add("A command must be defined for `docker exec`-based health checks.");
      }
    } else if (healthCheck instanceof HttpHealthCheck || healthCheck instanceof TcpHealthCheck) {
      final String port;
      if (healthCheck instanceof HttpHealthCheck) {
        port = ((HttpHealthCheck) healthCheck).getPort();
      } else {
        port = ((TcpHealthCheck) healthCheck).getPort();
      }

      final Map<String, PortMapping> ports = job.getPorts();
      if (isNullOrEmpty(port)) {
        errors.add("A port must be defined for HTTP and TCP health checks.");
      } else if (!ports.containsKey(port)) {
        errors.add(format("Health check port '%s' not defined in the job. Known ports are '%s'",
                          port, Joiner.on(", ").join(ports.keySet())));
      }
    }

    return errors;
  }

  private boolean legalPort(final int port) {
    return port >= 0 && port <= 65535;
  }
}


File: helios-client/src/main/java/com/spotify/helios/common/descriptors/Job.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.common.descriptors;

import com.google.common.base.Objects;
import com.google.common.base.Optional;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import com.google.common.io.BaseEncoding;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.spotify.helios.common.Json;

import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.io.IOException;
import java.util.Date;
import java.util.List;
import java.util.Map;

import static com.google.common.base.Charsets.UTF_8;
import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Throwables.propagate;
import static com.spotify.helios.common.Hash.sha1digest;
import static java.util.Collections.emptyList;
import static java.util.Collections.emptyMap;

/**
 * Represents a Helios job.
 *
 * An sample expression of it in JSON might be:
 * <pre>
 * {
 *   "command" : [ "server", "serverconfig.yaml" ],
 *   "env" : {
 *     "JVM_ARGS" : "-Ddw.feature.randomFeatureFlagEnabled=true"
 *   },
 *   "expires" : null,
 *   "gracePeriod": 60,
 *   "healthCheck" : {
 *     "type" : "http",
 *     "path" : "/healthcheck",
 *     "port" : "http-admin"
 *   },
 *   "id" : "myservice:0.5:3539b7bc2235d53f79e6e8511942bbeaa8816265",
 *   "image" : "myregistry:80/janedoe/myservice:0.5-98c6ff4",
 *   "networkMode" : "bridge",
 *   "ports" : {
 *     "http" : {
 *       "externalPort" : 8060,
 *       "internalPort" : 8080,
 *       "protocol" : "tcp"
 *     },
 *     "http-admin" : {
 *       "externalPort" : 8061,
 *       "internalPort" : 8081,
 *       "protocol" : "tcp"
 *     }
 *   },
 *   "registration" : {
 *     "service/http" : {
 *       "ports" : {
 *         "http" : { }
 *       }
 *     }
 *   },
 *   "registrationDomain" : "",
 *   "securityOpt" : [ "label:user:USER", "apparmor:PROFILE" ],
 *   "token": "insecure-access-token",
 *   "volumes" : {
 *     "/destination/path/in/container.yaml:ro" : "/source/path/in/host.yaml"
 *   }
 * }
 * </pre>
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Job extends Descriptor implements Comparable<Job> {

  public static final Map<String, String> EMPTY_ENV = emptyMap();
  public static final Resources EMPTY_RESOURCES = null;
  public static final Map<String, PortMapping> EMPTY_PORTS = emptyMap();
  public static final List<String> EMPTY_COMMAND = emptyList();
  public static final Map<ServiceEndpoint, ServicePorts> EMPTY_REGISTRATION = emptyMap();
  public static final Integer EMPTY_GRACE_PERIOD = null;
  public static final Map<String, String> EMPTY_VOLUMES = emptyMap();
  public static final String EMPTY_MOUNT = "";
  public static final Date EMPTY_EXPIRES = null;
  public static final String EMPTY_REGISTRATION_DOMAIN = "";
  public static final String EMPTY_CREATING_USER = null;
  public static final String EMPTY_TOKEN = "";
  public static final HealthCheck EMPTY_HEALTH_CHECK = null;
  public static final List<String> EMPTY_SECURITY_OPT = emptyList();
  public static final String EMPTY_NETWORK_MODE = null;

  private final JobId id;
  private final String image;
  private final List<String> command;
  private final Map<String, String> env;
  private final Resources resources;
  private final Map<String, PortMapping> ports;
  private final Map<ServiceEndpoint, ServicePorts> registration;
  private final Integer gracePeriod;
  private final Map<String, String> volumes;
  private final Date expires;
  private final String registrationDomain;
  private final String creatingUser;
  private final String token;
  private final HealthCheck healthCheck;
  private final List<String> securityOpt;
  private final String networkMode;

  /**
   * Create a Job.
   *
   * @param id The id of the job.
   * @param image The docker image to use.
   * @param command The command to pass to the container.
   * @param env Environment variables to set
   * @param resources Resource specification for the container.
   * @param ports The ports you wish to expose from the container.
   * @param registration Configuration information for the discovery service (if applicable)
   * @param gracePeriod How long to let the container run after deregistering with the discovery
   *    service.  If nothing is configured in registration, this option is ignored.
   * @param volumes Docker volumes to mount.
   * @param expires If set, a timestamp at which the job and any deployments will be removed.
   * @param registrationDomain If set, overrides the default domain in which discovery service
   *    registration occurs.  What is allowed here will vary based upon the discovery service
   *    plugin used.
   * @param creatingUser The user creating the job.
   * @param token The token needed to manipulate this job.
   * @param healthCheck A health check Helios will execute on the container.
   * @param securityOpt A list of strings denoting security options for running Docker containers,
   *    i.e. `docker run --security-opt`.
   *    See <a href="https://docs.docker.com/reference/run/#security-configuration">Docker docs</a>.
   * @param networkMode Sets the networking mode for the container. Supported values are: bridge,
   *    host, and container:&lt;name|id&gt;.
   *    See <a href="https://docs.docker.com/reference/run/#network-settings">Docker docs</a>.
   * @see <a href="https://docs.docker.com/reference/run/#network-settings">Docker run reference</a>
   */
  public Job(@JsonProperty("id") final JobId id,
             @JsonProperty("image") final String image,
             @JsonProperty("command") @Nullable final List<String> command,
             @JsonProperty("env") @Nullable final Map<String, String> env,
             @JsonProperty("resources") @Nullable final Resources resources,
             @JsonProperty("ports") @Nullable final Map<String, PortMapping> ports,
             @JsonProperty("registration") @Nullable
                 final Map<ServiceEndpoint, ServicePorts> registration,
             @JsonProperty("gracePeriod") @Nullable final Integer gracePeriod,
             @JsonProperty("volumes") @Nullable final Map<String, String> volumes,
             @JsonProperty("expires") @Nullable final Date expires,
             @JsonProperty("registrationDomain") @Nullable String registrationDomain,
             @JsonProperty("creatingUser") @Nullable String creatingUser,
             @JsonProperty("token") @Nullable String token,
             @JsonProperty("healthCheck") @Nullable HealthCheck healthCheck,
             @JsonProperty("securityOpt") @Nullable final List<String> securityOpt,
             @JsonProperty("networkMode") @Nullable final String networkMode) {
    this.id = id;
    this.image = image;

    // Optional
    this.command = Optional.fromNullable(command).or(EMPTY_COMMAND);
    this.env = Optional.fromNullable(env).or(EMPTY_ENV);
    this.resources = Optional.fromNullable(resources).orNull();
    this.ports = Optional.fromNullable(ports).or(EMPTY_PORTS);
    this.registration = Optional.fromNullable(registration).or(EMPTY_REGISTRATION);
    this.gracePeriod = Optional.fromNullable(gracePeriod).orNull();
    this.volumes = Optional.fromNullable(volumes).or(EMPTY_VOLUMES);
    this.expires = expires;
    this.registrationDomain = Optional.fromNullable(registrationDomain)
        .or(EMPTY_REGISTRATION_DOMAIN);
    this.creatingUser = Optional.fromNullable(creatingUser).orNull();
    this.token = Optional.fromNullable(token).or(EMPTY_TOKEN);
    this.healthCheck = Optional.fromNullable(healthCheck).orNull();
    this.securityOpt = Optional.fromNullable(securityOpt).or(EMPTY_SECURITY_OPT);
    this.networkMode = Optional.fromNullable(networkMode).orNull();
  }

  private Job(final JobId id, final Builder.Parameters p) {
    this.id = id;
    this.image = p.image;

    this.command = ImmutableList.copyOf(checkNotNull(p.command, "command"));
    this.env = ImmutableMap.copyOf(checkNotNull(p.env, "env"));
    this.resources = p.resources;
    this.ports = ImmutableMap.copyOf(checkNotNull(p.ports, "ports"));
    this.registration = ImmutableMap.copyOf(checkNotNull(p.registration, "registration"));
    this.gracePeriod = p.gracePeriod;
    this.volumes = ImmutableMap.copyOf(checkNotNull(p.volumes, "volumes"));
    this.expires = p.expires;
    this.registrationDomain = Optional.fromNullable(p.registrationDomain)
        .or(EMPTY_REGISTRATION_DOMAIN);
    this.creatingUser = p.creatingUser;
    this.token = p.token;
    this.healthCheck = p.healthCheck;
    this.securityOpt = p.securityOpt;
    this.networkMode = p.networkMode;
  }

  public JobId getId() {
    return id;
  }

  public String getImage() {
    return image;
  }

  public List<String> getCommand() {
    return command;
  }

  public Map<String, String> getEnv() {
    return env;
  }

  public Resources getResources() {
    return resources;
  }

  public Map<String, PortMapping> getPorts() {
    return ports;
  }

  public Map<ServiceEndpoint, ServicePorts> getRegistration() {
    return registration;
  }

  public String getRegistrationDomain() {
    return registrationDomain;
  }

  public Integer getGracePeriod() {
    return gracePeriod;
  }

  public Map<String, String> getVolumes() {
    return volumes;
  }

  public Date getExpires() {
    return expires;
  }

  public String getCreatingUser() {
    return creatingUser;
  }

  public String getToken() {
    return token;
  }

  public HealthCheck getHealthCheck() {
    return healthCheck;
  }

  public List<String> getSecurityOpt() {
    return securityOpt;
  }

  public String getNetworkMode() {
    return networkMode;
  }

  public static Builder newBuilder() {
    return new Builder();
  }

  @Override
  public int compareTo(@NotNull final Job o) {
    return id.compareTo(o.getId());
  }

  @Override
  public boolean equals(final Object o) {
    if (this == o) {
      return true;
    }
    if (o == null || getClass() != o.getClass()) {
      return false;
    }

    final Job job = (Job) o;

    if (command != null ? !command.equals(job.command) : job.command != null) {
      return false;
    }
    if (env != null ? !env.equals(job.env) : job.env != null) {
      return false;
    }
    if (resources != null ? !resources.equals(job.resources) : job.resources != null) {
      return false;
    }
    if (expires != null ? !expires.equals(job.expires) : job.expires != null) {
      return false;
    }
    if (id != null ? !id.equals(job.id) : job.id != null) {
      return false;
    }
    if (image != null ? !image.equals(job.image) : job.image != null) {
      return false;
    }
    if (ports != null ? !ports.equals(job.ports) : job.ports != null) {
      return false;
    }
    if (registration != null ? !registration.equals(job.registration) : job.registration != null) {
      return false;
    }
    if (registrationDomain != null
        ? !registrationDomain.equals(job.registrationDomain)
        : job.registrationDomain != null) {
      return false;
    }
    if (gracePeriod != null ? !gracePeriod.equals(job.gracePeriod) : job.gracePeriod != null) {
      return false;
    }
    if (volumes != null ? !volumes.equals(job.volumes) : job.volumes != null) {
      return false;
    }
    if (creatingUser != null ? !creatingUser.equals(job.creatingUser) : job.creatingUser != null) {
      return false;
    }
    if (!token.equals(job.token)) {
      return false;
    }
    if (healthCheck != null ? !healthCheck.equals(job.healthCheck) : job.healthCheck != null) {
      return false;
    }
    if (securityOpt != null ? !securityOpt.equals(job.securityOpt) : job.securityOpt != null) {
      return false;
    }
    if (networkMode != null ? !networkMode.equals(job.networkMode) : job.networkMode != null) {
      return false;
    }

    return true;
  }

  @Override
  public int hashCode() {
    int result = id != null ? id.hashCode() : 0;
    result = 31 * result + (image != null ? image.hashCode() : 0);
    result = 31 * result + (expires != null ? expires.hashCode() : 0);
    result = 31 * result + (command != null ? command.hashCode() : 0);
    result = 31 * result + (env != null ? env.hashCode() : 0);
    result = 31 * result + (resources != null ? resources.hashCode() : 0);
    result = 31 * result + (ports != null ? ports.hashCode() : 0);
    result = 31 * result + (registration != null ? registration.hashCode() : 0);
    result = 31 * result + (registrationDomain != null ? registrationDomain.hashCode() : 0);
    result = 31 * result + (gracePeriod != null ? gracePeriod.hashCode() : 0);
    result = 31 * result + (volumes != null ? volumes.hashCode() : 0);
    result = 31 * result + (creatingUser != null ? creatingUser.hashCode() : 0);
    result = 31 * result + token.hashCode();
    result = 31 * result + (healthCheck != null ? healthCheck.hashCode() : 0);
    result = 31 * result + (securityOpt != null ? securityOpt.hashCode() : 0);
    result = 31 * result + (networkMode != null ? networkMode.hashCode() : 0);
    return result;
  }

  @Override
  public String toString() {
    return Objects.toStringHelper(this)
        .add("id", id)
        .add("image", image)
        .add("command", command)
        .add("env", env)
        .add("resources", resources)
        .add("ports", ports)
        .add("registration", registration)
        .add("gracePeriod", gracePeriod)
        .add("expires", expires)
        .add("registrationDomain", registrationDomain)
        .add("creatingUser", creatingUser)
        .add("token", token)
        .add("healthCheck", healthCheck)
        .add("securityOpt", securityOpt)
        .add("networkMode", networkMode)
        .toString();
  }

  public Builder toBuilder() {
    final Builder builder = newBuilder();

    if (id != null) {
      builder.setName(id.getName())
          .setVersion(id.getVersion());
    }

    return builder.setImage(image)
        .setCommand(command)
        .setEnv(env)
        .setResources(resources)
        .setPorts(ports)
        .setRegistration(registration)
        .setGracePeriod(gracePeriod)
        .setVolumes(volumes)
        .setExpires(expires)
        .setRegistrationDomain(registrationDomain)
        .setCreatingUser(creatingUser)
        .setToken(token)
        .setHealthCheck(healthCheck)
        .setSecurityOpt(securityOpt)
        .setNetworkMode(networkMode);
  }

  public static class Builder implements Cloneable {

    private final Parameters p;
    private String hash;

    private Builder() {
      this.p = new Parameters();
    }

    public Builder(final String hash, final Parameters parameters) {
      this.hash = hash;
      this.p = parameters;
    }

    private static class Parameters implements Cloneable {

      public String registrationDomain;
      public String name;
      public String version;
      public String image;
      public List<String> command;
      public Map<String, String> env;
      public Resources resources;
      public Map<String, PortMapping> ports;
      public Map<ServiceEndpoint, ServicePorts> registration;
      public Integer gracePeriod;
      public Map<String, String> volumes;
      public Date expires;
      public String creatingUser;
      public String token;
      public HealthCheck healthCheck;
      public List<String> securityOpt;
      public String networkMode;

      private Parameters() {
        this.command = EMPTY_COMMAND;
        this.env = Maps.newHashMap(EMPTY_ENV);
        this.resources = EMPTY_RESOURCES;
        this.ports = Maps.newHashMap(EMPTY_PORTS);
        this.registration = Maps.newHashMap(EMPTY_REGISTRATION);
        this.gracePeriod = EMPTY_GRACE_PERIOD;
        this.volumes = Maps.newHashMap(EMPTY_VOLUMES);
        this.registrationDomain = EMPTY_REGISTRATION_DOMAIN;
        this.creatingUser = EMPTY_CREATING_USER;
        this.token = EMPTY_TOKEN;
        this.healthCheck = EMPTY_HEALTH_CHECK;
        this.securityOpt = EMPTY_SECURITY_OPT;
      }

      private Parameters(final Parameters p) {
        this.name = p.name;
        this.version = p.version;
        this.image = p.image;
        this.command = ImmutableList.copyOf(p.command);
        this.env = Maps.newHashMap(p.env);
        this.resources = p.resources;
        this.ports = Maps.newHashMap(p.ports);
        this.registration = Maps.newHashMap(p.registration);
        this.gracePeriod = p.gracePeriod;
        this.volumes = Maps.newHashMap(p.volumes);
        this.expires = p.expires;
        this.registrationDomain = p.registrationDomain;
        this.creatingUser = p.creatingUser;
        this.token = p.token;
        this.healthCheck = p.healthCheck;
        this.securityOpt = p.securityOpt;
        this.networkMode = p.networkMode;
      }
    }

    public Builder setRegistrationDomain(final String domain) {
      this.p.registrationDomain = domain;
      return this;
    }

    public Builder setCreatingUser(final String creatingUser) {
      this.p.creatingUser = creatingUser;
      return this;
    }

    public Builder setToken(final String token) {
      this.p.token = token;
      return this;
    }

    public Builder setHash(final String hash) {
      this.hash = hash;
      return this;
    }

    public Builder setName(final String name) {
      p.name = name;
      return this;
    }

    public Builder setVersion(final String version) {
      p.version = version;
      return this;
    }

    public Builder setImage(final String image) {
      p.image = image;
      return this;
    }

    public Builder setCommand(final List<String> command) {
      p.command = ImmutableList.copyOf(command);
      return this;
    }

    public Builder setEnv(final Map<String, String> env) {
      p.env = Maps.newHashMap(env);
      return this;
    }

    public Builder setResources(final Resources resources) {
      p.resources = resources;
      return this;
    }

    public Builder addEnv(final String key, final String value) {
      p.env.put(key, value);
      return this;
    }

    public Builder setPorts(final Map<String, PortMapping> ports) {
      p.ports = Maps.newHashMap(ports);
      return this;
    }

    public Builder addPort(final String name, final PortMapping port) {
      p.ports.put(name, port);
      return this;
    }

    public Builder setRegistration(final Map<ServiceEndpoint, ServicePorts> registration) {
      p.registration = Maps.newHashMap(registration);
      return this;
    }

    public Builder addRegistration(final ServiceEndpoint endpoint, final ServicePorts ports) {
      p.registration.put(endpoint, ports);
      return this;
    }

    public Builder setGracePeriod(final Integer gracePeriod) {
      p.gracePeriod = gracePeriod;
      return this;
    }

    public Builder setVolumes(final Map<String, String> volumes) {
      p.volumes = Maps.newHashMap(volumes);
      return this;
    }

    public Builder addVolume(final String path) {
      p.volumes.put(path, EMPTY_MOUNT);
      return this;
    }

    public Builder addVolume(final String path, final String source) {
      p.volumes.put(path, source);
      return this;
    }

    public Builder setExpires(final Date expires) {
      p.expires = expires;
      return this;
    }

    public Builder setHealthCheck(final HealthCheck healthCheck) {
      p.healthCheck = healthCheck;
      return this;
    }

    public Builder setSecurityOpt(final List<String> securityOpt) {
      p.securityOpt = securityOpt;
      return this;
    }

    public Builder setNetworkMode(final String networkMode) {
      p.networkMode = networkMode;
      return this;
    }

    public String getName() {
      return p.name;
    }

    public String getVersion() {
      return p.version;
    }

    public String getImage() {
      return p.image;
    }

    public List<String> getCommand() {
      return p.command;
    }

    public Map<String, String> getEnv() {
      return ImmutableMap.copyOf(p.env);
    }

    public Map<String, PortMapping> getPorts() {
      return ImmutableMap.copyOf(p.ports);
    }

    public Map<ServiceEndpoint, ServicePorts> getRegistration() {
      return ImmutableMap.copyOf(p.registration);
    }

    public String getRegistrationDomain() {
      return p.registrationDomain;
    }

    public Integer getGracePeriod() {
      return p.gracePeriod;
    }

    public Map<String, String> getVolumes() {
      return ImmutableMap.copyOf(p.volumes);
    }

    public Date getExpires() {
      return p.expires;
    }

    public String getCreatingUser() {
      return p.creatingUser;
    }

    public Resources getResources() {
      return p.resources;
    }

    public HealthCheck getHealthCheck() {
      return p.healthCheck;
    }

    public List<String> getSecurityOpt() {
      return p.securityOpt;
    }

    public String getNetworkMode() {
      return p.networkMode;
    }

    @SuppressWarnings({"CloneDoesntDeclareCloneNotSupportedException", "CloneDoesntCallSuperClone"})
    @Override
    public Builder clone() {
      return new Builder(hash, new Parameters(p));
    }

    public Job build() {
      final String configHash;
      try {
        configHash = hex(Json.sha1digest(p));
      } catch (IOException e) {
        throw propagate(e);
      }

      final String hash;
      if (!Strings.isNullOrEmpty(this.hash)) {
        hash = this.hash;
      } else {
        if (p.name != null && p.version != null) {
          final String input = String.format("%s:%s:%s", p.name, p.version, configHash);
          hash = hex(sha1digest(input.getBytes(UTF_8)));
        } else {
          hash = null;
        }
      }

      final JobId id = new JobId(p.name, p.version, hash);

      return new Job(id, p);
    }

    private String hex(final byte[] bytes) {
      return BaseEncoding.base16().lowerCase().encode(bytes);
    }
  }
}


File: helios-client/src/test/java/com/spotify/helios/common/JobValidatorTest.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.common;

import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;

import com.spotify.helios.common.descriptors.HealthCheck;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.PortMapping;
import com.spotify.helios.common.descriptors.ServiceEndpoint;
import com.spotify.helios.common.descriptors.ServicePortParameters;
import com.spotify.helios.common.descriptors.ServicePorts;

import org.junit.Test;

import java.util.Map;

import static com.google.common.collect.Sets.newHashSet;
import static com.spotify.helios.common.descriptors.Job.EMPTY_COMMAND;
import static com.spotify.helios.common.descriptors.Job.EMPTY_CREATING_USER;
import static com.spotify.helios.common.descriptors.Job.EMPTY_ENV;
import static com.spotify.helios.common.descriptors.Job.EMPTY_EXPIRES;
import static com.spotify.helios.common.descriptors.Job.EMPTY_GRACE_PERIOD;
import static com.spotify.helios.common.descriptors.Job.EMPTY_HEALTH_CHECK;
import static com.spotify.helios.common.descriptors.Job.EMPTY_NETWORK_MODE;
import static com.spotify.helios.common.descriptors.Job.EMPTY_PORTS;
import static com.spotify.helios.common.descriptors.Job.EMPTY_REGISTRATION;
import static com.spotify.helios.common.descriptors.Job.EMPTY_REGISTRATION_DOMAIN;
import static com.spotify.helios.common.descriptors.Job.EMPTY_RESOURCES;
import static com.spotify.helios.common.descriptors.Job.EMPTY_SECURITY_OPT;
import static com.spotify.helios.common.descriptors.Job.EMPTY_TOKEN;
import static com.spotify.helios.common.descriptors.Job.EMPTY_VOLUMES;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.core.Is.is;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThat;

public class JobValidatorTest {
  private final HealthCheck HEALTH_CHECK =
    HealthCheck.newHttpHealthCheck().setPath("/").setPort("1").build();
  private final Job VALID_JOB = Job.newBuilder()
      .setName("foo")
      .setVersion("1")
      .setImage("bar")
      .setEnv(ImmutableMap.of("FOO", "BAR"))
      .setPorts(ImmutableMap.of("1", PortMapping.of(1, 1),
                                "2", PortMapping.of(2, 2)))
      .setHealthCheck(HEALTH_CHECK)
      .build();

  final JobValidator validator = new JobValidator();

  @Test
  public void testValidJobPasses() {
    assertThat(validator.validate(VALID_JOB), is(empty()));
  }

  @Test
  public void testValidNamesPass() {
    final Job.Builder b = Job.newBuilder().setVersion("1").setImage("bar");
    assertThat(validator.validate(b.setName("foo").build()), is(empty()));
    assertThat(validator.validate(b.setName("17").build()), is(empty()));
    assertThat(validator.validate(b.setName("foo17.bar-baz_quux").build()), is(empty()));
  }

  @Test
  public void testValidVersionsPass() {
    final Job.Builder b = Job.newBuilder().setName("foo").setImage("bar");
    assertThat(validator.validate(b.setVersion("foo").build()), is(empty()));
    assertThat(validator.validate(b.setVersion("17").build()), is(empty()));
    assertThat(validator.validate(b.setVersion("foo17.bar-baz_quux").build()), is(empty()));
  }

  @Test
  public void testValidImagePasses() {
    final Job.Builder b = Job.newBuilder().setName("foo").setVersion("1");
    assertThat(validator.validate(b.setImage("repo").build()), is(empty()));
    assertThat(validator.validate(b.setImage("namespace/repo").build()), is(empty()));
    assertThat(validator.validate(b.setImage("namespace/repo:tag").build()), is(empty()));
    assertThat(validator.validate(b.setImage("namespace/repo:1.2").build()), is(empty()));
    assertThat(validator.validate(b.setImage("reg.istry:4711/repo").build()), is(empty()));
    assertThat(validator.validate(b.setImage("reg.istry.:4711/repo").build()), is(empty()));
    assertThat(validator.validate(b.setImage("reg.istry:4711/namespace/repo").build()),
               is(empty()));
    assertThat(validator.validate(b.setImage("reg.istry.:4711/namespace/repo").build()),
               is(empty()));
    assertThat(validator.validate(b.setImage("1.2.3.4:4711/namespace/repo").build()), is(empty()));
    assertThat(validator.validate(b.setImage("registry.test.net:80/fooo/bar").build()),
               is(empty()));
    assertThat(validator.validate(b.setImage("registry.test.net.:80/fooo/bar").build()),
               is(empty()));
  }

  @Test
  public void testValidVolumesPass() {
    final Job j = Job.newBuilder().setName("foo").setVersion("1").setImage("foobar").build();
    assertThat(validator.validate(j.toBuilder().addVolume("/foo").build()), is(empty()));
    assertThat(validator.validate(j.toBuilder().addVolume("/foo", "/").build()), is(empty()));
    assertThat(validator.validate(j.toBuilder().addVolume("/foo:ro", "/").build()), is(empty()));
    assertThat(validator.validate(j.toBuilder().addVolume("/foo", "/bar").build()), is(empty()));
    assertThat(validator.validate(j.toBuilder().addVolume("/foo:ro", "/bar").build()), is(empty()));
  }

  @Test
  public void testValidPortTagsPass() {
    final Job j = Job.newBuilder().setName("foo").setVersion("1").setImage("foobar").build();
    final Job.Builder builder = j.toBuilder();
    final Map<String, PortMapping> ports = ImmutableMap.of("add_ports1", PortMapping.of(1234),
                                                           "add_ports2", PortMapping.of(2345));
    final ImmutableMap.Builder<String, ServicePortParameters> servicePortsBuilder =
        ImmutableMap.builder();
    servicePortsBuilder.put("add_ports1", new ServicePortParameters(
        ImmutableList.of("tag1", "tag2")));
    servicePortsBuilder.put("add_ports2", new ServicePortParameters(
        ImmutableList.of("tag3", "tag4")));
    final ServicePorts servicePorts = new ServicePorts(servicePortsBuilder.build());
    final Map<ServiceEndpoint, ServicePorts> addRegistration = ImmutableMap.of(
        ServiceEndpoint.of("add_service", "add_proto"), servicePorts);
    builder.setPorts(ports).setRegistration(addRegistration);
    assertThat(validator.validate(builder.build()), is(empty()));
  }

  @Test
  public void testPortMappingCollisionFails() throws Exception {
    final Job job = Job.newBuilder()
        .setName("foo")
        .setVersion("1")
        .setImage("bar")
        .setPorts(ImmutableMap.of("1", PortMapping.of(1, 1),
                                  "2", PortMapping.of(2, 1)))
        .build();

    assertEquals(ImmutableSet.of("Duplicate external port mapping: 1"), validator.validate(job));
  }

  @Test
  public void testIdMismatchFails() throws Exception {
    final Job job = new Job(JobId.fromString("foo:bar:badf00d"),
                            "bar", EMPTY_COMMAND, EMPTY_ENV, EMPTY_RESOURCES, EMPTY_PORTS,
                            EMPTY_REGISTRATION, EMPTY_GRACE_PERIOD, EMPTY_VOLUMES, EMPTY_EXPIRES,
                            EMPTY_REGISTRATION_DOMAIN, EMPTY_CREATING_USER, EMPTY_TOKEN,
                            EMPTY_HEALTH_CHECK, EMPTY_SECURITY_OPT, EMPTY_NETWORK_MODE);
    final JobId recomputedId = job.toBuilder().build().getId();
    assertEquals(ImmutableSet.of("Id hash mismatch: " + job.getId().getHash()
        + " != " + recomputedId.getHash()), validator.validate(job));
  }

  @Test
  public void testInvalidNamesFail() throws Exception {
    final Job.Builder b = Job.newBuilder().setVersion("1").setImage("foo");
    assertEquals(newHashSet("Job name was not specified.",
        "Job hash was not specified in job id [null:1]."),
                 validator.validate(b.build()));
    assertThat(validator.validate(b.setName("foo@bar").build()),
               contains(
                   equalTo("Job name may only contain [0-9a-zA-Z-_.] in job name [foo@bar].")));
    assertThat(validator.validate(b.setName("foo&bar").build()),
               contains(
                   equalTo("Job name may only contain [0-9a-zA-Z-_.] in job name [foo&bar].")));
  }

  @Test
  public void testInvalidVersionsFail() throws Exception {
    final Job.Builder b = Job.newBuilder().setName("foo").setImage("foo");
    assertEquals(newHashSet("Job version was not specified in job id [foo:null].",
        "Job hash was not specified in job id [foo:null]."),
                 validator.validate(b.build()));
    assertThat(validator.validate(b.setVersion("17@bar").build()),
               contains(equalTo("Job version may only contain [0-9a-zA-Z-_.] "
                   + "in job version [17@bar].")));
    assertThat(validator.validate(b.setVersion("17&bar").build()),
               contains(equalTo("Job version may only contain [0-9a-zA-Z-_.] "
                   + "in job version [17&bar].")));
  }


  @Test
  public void testInvalidImagesFail() throws Exception {
    final Job.Builder b = Job.newBuilder().setName("foo").setVersion("1");

    assertEquals(newHashSet("Tag cannot be empty"),
                 validator.validate(b.setImage("repo:").build()));

    assertFalse(validator.validate(b.setImage("repo:/").build()).isEmpty());

    assertEquals(newHashSet("Invalid domain name: \"1.2.3.4.\""),
                 validator.validate(b.setImage("1.2.3.4.:4711/namespace/repo").build()));

    assertEquals(newHashSet("Invalid domain name: \" reg.istry\""),
                 validator.validate(b.setImage(" reg.istry:4711/repo").build()));

    assertEquals(newHashSet("Invalid domain name: \"reg .istry\""),
                 validator.validate(b.setImage("reg .istry:4711/repo").build()));

    assertEquals(newHashSet("Invalid domain name: \"reg.istry \""),
                 validator.validate(b.setImage("reg.istry :4711/repo").build()));

    assertEquals(newHashSet("Invalid port in endpoint: \"reg.istry: 4711\""),
                 validator.validate(b.setImage("reg.istry: 4711/repo").build()));

    assertEquals(newHashSet("Invalid port in endpoint: \"reg.istry:4711 \""),
                 validator.validate(b.setImage("reg.istry:4711 /repo").build()));

    assertEquals(newHashSet("Invalid repository name ( repo), only [a-z0-9-_.] are allowed"),
                 validator.validate(b.setImage("reg.istry:4711/ repo").build()));

    assertEquals(newHashSet("Invalid namespace name (namespace ), only [a-z0-9_] are " +
                            "allowed, size between 4 and 30"),
                 validator.validate(b.setImage("reg.istry:4711/namespace /repo").build()));

    assertEquals(newHashSet("Invalid repository name ( repo), only [a-z0-9-_.] are allowed"),
                 validator.validate(b.setImage("reg.istry:4711/namespace/ repo").build()));

    assertEquals(newHashSet("Invalid repository name (repo ), only [a-z0-9-_.] are allowed"),
                 validator.validate(b.setImage("reg.istry:4711/namespace/repo ").build()));

    assertEquals(newHashSet("Invalid domain name: \"foo-.ba|z\""),
                 validator.validate(b.setImage("foo-.ba|z/namespace/baz").build()));

    assertEquals(newHashSet("Invalid domain name: \"reg..istry\""),
                 validator.validate(b.setImage("reg..istry/namespace/baz").build()));

    assertEquals(newHashSet("Invalid domain name: \"reg..istry\""),
                 validator.validate(b.setImage("reg..istry/namespace/baz").build()));

    assertEquals(newHashSet("Invalid port in endpoint: \"foo:345345345\""),
                 validator.validate(b.setImage("foo:345345345/namespace/baz").build()));

    assertEquals(newHashSet("Invalid port in endpoint: \"foo:-17\""),
                 validator.validate(b.setImage("foo:-17/namespace/baz").build()));

    assertEquals(newHashSet("Invalid repository name (bar/baz/quux), only [a-z0-9-_.] are allowed"),
                 validator.validate(b.setImage("foos/bar/baz/quux").build()));

    assertEquals(newHashSet("Invalid namespace name (foo), only [a-z0-9_] are allowed, " +
                            "size between 4 and 30"),
                 validator.validate(b.setImage("foo/bar").build()));

    final String foos = Strings.repeat("foo", 100);
    assertEquals(newHashSet("Invalid namespace name (" + foos + "), only [a-z0-9_] are allowed, " +
                            "size between 4 and 30"),
                 validator.validate(b.setImage(foos + "/bar").build()));
  }

  @Test
  public void testInvalidVolumesFail() {
    final Job j = Job.newBuilder().setName("foo").setVersion("1").setImage("foobar").build();
    assertEquals(newHashSet("Invalid volume path: /"),
                 validator.validate(j.toBuilder().addVolume("/").build()));

    assertEquals(newHashSet("Invalid volume path: /foo:"),
                 validator.validate(j.toBuilder().addVolume("/foo:", "/bar").build()));

    assertEquals(newHashSet("Volume path is not absolute: foo"),
                 validator.validate(j.toBuilder().addVolume("foo").build()));

    assertEquals(newHashSet("Volume path is not absolute: foo"),
                 validator.validate(j.toBuilder().addVolume("foo", "/bar").build()));

    assertEquals(newHashSet("Volume source is not absolute: bar"),
                 validator.validate(j.toBuilder().addVolume("/foo", "bar").build()));
  }

  @Test
  public void testInvalidHealthCheckFail() {
    final Job jobWithNoPorts = Job.newBuilder()
        .setName("foo")
        .setVersion("1")
        .setImage("foobar")
        .setHealthCheck(HEALTH_CHECK)
        .build();

    assertEquals(1, validator.validate(jobWithNoPorts).size());

    final Job jobWithWrongPort = jobWithNoPorts.toBuilder()
        .addPort("a", PortMapping.of(1, 1))
        .build();
    assertEquals(1, validator.validate(jobWithWrongPort).size());
  }
  
  @Test
  public void testExpiry() {
    // make a date that's 24 hours behind
    final java.util.Date d = new java.util.Date(System.currentTimeMillis() - (86400 * 1000));
    final Job j = Job.newBuilder().setName("foo").setVersion("1").setImage("foobar")
        .setExpires(d).build();
    assertEquals(newHashSet("Job expires in the past"), validator.validate(j));
  }
}


File: helios-client/src/test/java/com/spotify/helios/common/descriptors/JobTest.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.common.descriptors;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.io.BaseEncoding;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.spotify.helios.common.Hash;
import com.spotify.helios.common.Json;

import org.junit.Test;

import java.io.IOException;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.google.common.base.Charsets.UTF_8;
import static com.google.common.base.Preconditions.checkArgument;
import static com.spotify.helios.common.descriptors.Descriptor.parse;
import static java.util.Arrays.asList;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;

public class JobTest {

  private Map<String, Object> map(final Object... objects) {
    final ImmutableMap.Builder<String, Object> builder = ImmutableMap.builder();
    checkArgument(objects.length % 2 == 0);
    for (int i = 0; i < objects.length; i += 2) {
      builder.put((String) objects[i], objects[i + 1]);
    }
    return builder.build();
  }

  @Test
  public void testNormalizedExcludesEmptyStrings() throws Exception {
    final Job j = Job.newBuilder().setName("x").setImage("x").setVersion("x")
        .setRegistrationDomain("").build();
    assertFalse(Json.asNormalizedString(j).contains("registrationDomain"));
  }

  @Test
  public void verifyBuilder() throws Exception {
    final Job.Builder builder = Job.newBuilder();

    // Input to setXXX
    final String setName = "set_name";
    final String setVersion = "set_version";
    final String setImage = "set_image";
    final List<String> setCommand = asList("set", "command");
    final Map<String, String> setEnv = ImmutableMap.of("set", "env");
    final Map<String, PortMapping> setPorts = ImmutableMap.of("set_ports", PortMapping.of(1234));
    final ImmutableMap.Builder<String, ServicePortParameters> setServicePortsBuilder =
        ImmutableMap.builder();
    setServicePortsBuilder.put("set_ports1", new ServicePortParameters(
        ImmutableList.of("tag1", "tag2")));
    setServicePortsBuilder.put("set_ports2", new ServicePortParameters(
        ImmutableList.of("tag3", "tag4")));
    final ServicePorts setServicePorts = new ServicePorts(setServicePortsBuilder.build());
    final Map<ServiceEndpoint, ServicePorts> setRegistration = ImmutableMap.of(
        ServiceEndpoint.of("set_service", "set_proto"), setServicePorts);
    final Integer setGracePeriod = 120;
    final Map<String, String> setVolumes = ImmutableMap.of("/set", "/volume");
    final Date setExpires = new Date();
    final String setRegistrationDomain = "my.domain";
    final String setCreatingUser = "username";
    final Resources setResources = new Resources(10485760L, 10485761L, 4L, "1");
    final HealthCheck setHealthCheck = HealthCheck.newHttpHealthCheck()
        .setPath("/healthcheck")
        .setPort("set_ports")
        .build();
    final List<String> setSecurityOpt = Lists.newArrayList("label:user:dxia", "apparmor:foo");
    final String setNetworkMode = "host";

    // Input to addXXX
    final Map<String, String> addEnv = ImmutableMap.of("add", "env");
    final Map<String, PortMapping> addPorts = ImmutableMap.of("add_ports", PortMapping.of(4711));
    final ImmutableMap.Builder<String, ServicePortParameters> addServicePortsBuilder =
        ImmutableMap.builder();
    addServicePortsBuilder.put("add_ports1", new ServicePortParameters(
        ImmutableList.of("tag1", "tag2")));
    addServicePortsBuilder.put("add_ports2", new ServicePortParameters(
        ImmutableList.of("tag3", "tag4")));
    final ServicePorts addServicePorts = new ServicePorts(addServicePortsBuilder.build());
    final Map<ServiceEndpoint, ServicePorts> addRegistration = ImmutableMap.of(
        ServiceEndpoint.of("add_service", "add_proto"), addServicePorts);
    final Map<String, String> addVolumes = ImmutableMap.of("/add", "/volume");

    // Expected output from getXXX
    final String expectedName = setName;
    final String expectedVersion = setVersion;
    final String expectedImage = setImage;
    final List<String> expectedCommand = setCommand;
    final Map<String, String> expectedEnv = concat(setEnv, addEnv);
    final Map<String, PortMapping> expectedPorts = concat(setPorts, addPorts);
    final Map<ServiceEndpoint, ServicePorts> expectedRegistration =
        concat(setRegistration, addRegistration);
    final Integer expectedGracePeriod = setGracePeriod;
    final Map<String, String> expectedVolumes = concat(setVolumes, addVolumes);
    final Date expectedExpires = setExpires;
    final String expectedRegistrationDomain = setRegistrationDomain;
    final String expectedCreatingUser = setCreatingUser;
    final Resources expectedResources = setResources;
    final HealthCheck expectedHealthCheck = setHealthCheck;
    final List<String> expectedSecurityOpt = setSecurityOpt;
    final String expectedNetworkMode = setNetworkMode;

    // Check setXXX methods
    builder.setName(setName);
    builder.setVersion(setVersion);
    builder.setImage(setImage);
    builder.setCommand(setCommand);
    builder.setEnv(setEnv);
    builder.setPorts(setPorts);
    builder.setRegistration(setRegistration);
    builder.setGracePeriod(setGracePeriod);
    builder.setVolumes(setVolumes);
    builder.setExpires(setExpires);
    builder.setRegistrationDomain(setRegistrationDomain);
    builder.setCreatingUser(setCreatingUser);
    builder.setResources(setResources);
    builder.setHealthCheck(setHealthCheck);
    builder.setSecurityOpt(setSecurityOpt);
    builder.setNetworkMode(setNetworkMode);
    assertEquals("name", setName, builder.getName());
    assertEquals("version", setVersion, builder.getVersion());
    assertEquals("image", setImage, builder.getImage());
    assertEquals("command", setCommand, builder.getCommand());
    assertEquals("env", setEnv, builder.getEnv());
    assertEquals("ports", setPorts, builder.getPorts());
    assertEquals("registration", setRegistration, builder.getRegistration());
    assertEquals("gracePeriod", setGracePeriod, builder.getGracePeriod());
    assertEquals("volumes", setVolumes, builder.getVolumes());
    assertEquals("expires", setExpires, builder.getExpires());
    assertEquals("registrationDomain", setRegistrationDomain, builder.getRegistrationDomain());
    assertEquals("creatingUser", setCreatingUser, builder.getCreatingUser());
    assertEquals("resources", setResources, builder.getResources());
    assertEquals("healthCheck", setHealthCheck, builder.getHealthCheck());
    assertEquals("securityOpt", setSecurityOpt, builder.getSecurityOpt());
    assertEquals("networkMode", setNetworkMode, builder.getNetworkMode());

    // Check addXXX methods
    for (final Map.Entry<String, String> entry : addEnv.entrySet()) {
      builder.addEnv(entry.getKey(), entry.getValue());
    }
    for (final Map.Entry<String, PortMapping> entry : addPorts.entrySet()) {
      builder.addPort(entry.getKey(), entry.getValue());
    }
    for (final Map.Entry<ServiceEndpoint, ServicePorts> entry : addRegistration.entrySet()) {
      builder.addRegistration(entry.getKey(), entry.getValue());
    }
    for (Map.Entry<String, String> entry : addVolumes.entrySet()) {
      builder.addVolume(entry.getKey(), entry.getValue());
    }
    assertEquals("name", expectedName, builder.getName());
    assertEquals("version", expectedVersion, builder.getVersion());
    assertEquals("image", expectedImage, builder.getImage());
    assertEquals("command", expectedCommand, builder.getCommand());
    assertEquals("env", expectedEnv, builder.getEnv());
    assertEquals("ports", expectedPorts, builder.getPorts());
    assertEquals("registration", expectedRegistration, builder.getRegistration());
    assertEquals("gracePeriod", expectedGracePeriod, builder.getGracePeriod());
    assertEquals("volumes", expectedVolumes, builder.getVolumes());
    assertEquals("expires", expectedExpires, builder.getExpires());
    assertEquals("registrationDomain", expectedRegistrationDomain, builder.getRegistrationDomain());
    assertEquals("creatingUser", expectedCreatingUser, builder.getCreatingUser());
    assertEquals("resources", expectedResources, builder.getResources());

    // Check final output
    final Job job = builder.build();
    assertEquals("name", expectedName, job.getId().getName());
    assertEquals("version", expectedVersion, job.getId().getVersion());
    assertEquals("image", expectedImage, job.getImage());
    assertEquals("command", expectedCommand, job.getCommand());
    assertEquals("env", expectedEnv, job.getEnv());
    assertEquals("ports", expectedPorts, job.getPorts());
    assertEquals("registration", expectedRegistration, job.getRegistration());
    assertEquals("gracePeriod", expectedGracePeriod, job.getGracePeriod());
    assertEquals("volumes", expectedVolumes, job.getVolumes());
    assertEquals("expires", expectedExpires, job.getExpires());
    assertEquals("registrationDomain", expectedRegistrationDomain, job.getRegistrationDomain());
    assertEquals("creatingUser", expectedCreatingUser, job.getCreatingUser());
    assertEquals("resources", expectedResources, job.getResources());
    assertEquals("healthCheck", expectedHealthCheck, job.getHealthCheck());
    assertEquals("securityOpt", expectedSecurityOpt, job.getSecurityOpt());
    assertEquals("networkMode", expectedNetworkMode, job.getNetworkMode());

    // Check toBuilder
    final Job.Builder rebuilder = job.toBuilder();
    assertEquals("name", expectedName, rebuilder.getName());
    assertEquals("version", expectedVersion, rebuilder.getVersion());
    assertEquals("image", expectedImage, rebuilder.getImage());
    assertEquals("command", expectedCommand, rebuilder.getCommand());
    assertEquals("env", expectedEnv, rebuilder.getEnv());
    assertEquals("ports", expectedPorts, rebuilder.getPorts());
    assertEquals("registration", expectedRegistration, rebuilder.getRegistration());
    assertEquals("gracePeriod", expectedGracePeriod, rebuilder.getGracePeriod());
    assertEquals("volumes", expectedVolumes, rebuilder.getVolumes());
    assertEquals("expires", expectedExpires, rebuilder.getExpires());
    assertEquals("registrationDomain", expectedRegistrationDomain,
        rebuilder.getRegistrationDomain());
    assertEquals("creatingUser", expectedCreatingUser, rebuilder.getCreatingUser());
    assertEquals("resources", expectedResources, rebuilder.getResources());
    assertEquals("healthCheck", expectedHealthCheck, rebuilder.getHealthCheck());
    assertEquals("securityOpt", expectedSecurityOpt, rebuilder.getSecurityOpt());
    assertEquals("networkMode", expectedNetworkMode, rebuilder.getNetworkMode());

    // Check clone
    final Job.Builder cloned = builder.clone();
    assertEquals("name", expectedName, cloned.getName());
    assertEquals("version", expectedVersion, cloned.getVersion());
    assertEquals("image", expectedImage, cloned.getImage());
    assertEquals("command", expectedCommand, cloned.getCommand());
    assertEquals("env", expectedEnv, cloned.getEnv());
    assertEquals("ports", expectedPorts, cloned.getPorts());
    assertEquals("registration", expectedRegistration, cloned.getRegistration());
    assertEquals("gracePeriod", expectedGracePeriod, cloned.getGracePeriod());
    assertEquals("volumes", expectedVolumes, cloned.getVolumes());
    assertEquals("expires", expectedExpires, cloned.getExpires());
    assertEquals("registrationDomain", expectedRegistrationDomain,
        cloned.getRegistrationDomain());
    assertEquals("creatingUser", expectedCreatingUser, cloned.getCreatingUser());
    assertEquals("resources", expectedResources, cloned.getResources());
    assertEquals("healthCheck", expectedHealthCheck, cloned.getHealthCheck());
    assertEquals("securityOpt", expectedSecurityOpt, cloned.getSecurityOpt());
    assertEquals("networkMode", expectedNetworkMode, cloned.getNetworkMode());

    final Job clonedJob = cloned.build();
    assertEquals("name", expectedName, clonedJob.getId().getName());
    assertEquals("version", expectedVersion, clonedJob.getId().getVersion());
    assertEquals("image", expectedImage, clonedJob.getImage());
    assertEquals("command", expectedCommand, clonedJob.getCommand());
    assertEquals("env", expectedEnv, clonedJob.getEnv());
    assertEquals("ports", expectedPorts, clonedJob.getPorts());
    assertEquals("registration", expectedRegistration, clonedJob.getRegistration());
    assertEquals("gracePeriod", expectedGracePeriod, clonedJob.getGracePeriod());
    assertEquals("volumes", expectedVolumes, clonedJob.getVolumes());
    assertEquals("expires", expectedExpires, clonedJob.getExpires());
    assertEquals("registrationDomain", expectedRegistrationDomain,
        clonedJob.getRegistrationDomain());
    assertEquals("creatingUser", expectedCreatingUser, clonedJob.getCreatingUser());
    assertEquals("resources", expectedResources, clonedJob.getResources());
    assertEquals("healthCheck", expectedHealthCheck, clonedJob.getHealthCheck());
    assertEquals("securityOpt", expectedSecurityOpt, clonedJob.getSecurityOpt());
    assertEquals("networkMode", expectedNetworkMode, clonedJob.getNetworkMode());
  }

  @SafeVarargs
  private final <K, V> Map<K, V> concat(final Map<K, V>... maps) {
    final ImmutableMap.Builder<K, V> b = ImmutableMap.builder();
    for (final Map<K, V> map : maps) {
      b.putAll(map);
    }
    return b.build();
  }

  @Test
  public void verifySha1ID() throws IOException {
    final Map<String, Object> expectedConfig = map("command", asList("foo", "bar"),
                                                   "image", "foobar:4711",
                                                   "name", "foozbarz",
                                                   "version", "17");

    final String expectedInput = "foozbarz:17:" + hex(Json.sha1digest(expectedConfig));
    final String expectedDigest = hex(Hash.sha1digest(expectedInput.getBytes(UTF_8)));
    final JobId expectedId = JobId.fromString("foozbarz:17:" + expectedDigest);

    final Job job = Job.newBuilder()
        .setCommand(asList("foo", "bar"))
        .setImage("foobar:4711")
        .setName("foozbarz")
        .setVersion("17")
        .build();

    assertEquals(expectedId, job.getId());
  }

  @Test
  public void verifySha1IDWithEnv() throws IOException {
    final Map<String, String> env = ImmutableMap.of("FOO", "BAR");
    final Map<String, Object> expectedConfig = map("command", asList("foo", "bar"),
                                                   "image", "foobar:4711",
                                                   "name", "foozbarz",
                                                   "version", "17",
                                                   "env", env);

    final String expectedInput = "foozbarz:17:" + hex(Json.sha1digest(expectedConfig));
    final String expectedDigest = hex(Hash.sha1digest(expectedInput.getBytes(UTF_8)));
    final JobId expectedId = JobId.fromString("foozbarz:17:" + expectedDigest);

    final Job job = Job.newBuilder()
        .setCommand(asList("foo", "bar"))
        .setImage("foobar:4711")
        .setName("foozbarz")
        .setVersion("17")
        .setEnv(env)
        .build();

    assertEquals(expectedId, job.getId());
  }

  private String hex(final byte[] bytes) {
    return BaseEncoding.base16().lowerCase().encode(bytes);
  }

  @Test
  public void verifyCanParseJobWithUnknownFields() throws Exception {
    final Job job = Job.newBuilder()
        .setCommand(asList("foo", "bar"))
        .setImage("foobar:4711")
        .setName("foozbarz")
        .setVersion("17")
        .build();

    final String jobJson = job.toJsonString();

    final ObjectMapper objectMapper = new ObjectMapper();
    final Map<String, Object> fields = objectMapper.readValue(
        jobJson, new TypeReference<Map<String, Object>>() {});
    fields.put("UNKNOWN_FIELD", "FOOBAR");
    final String modifiedJobJson = objectMapper.writeValueAsString(fields);

    final Job parsedJob = parse(modifiedJobJson, Job.class);

    assertEquals(job, parsedJob);
  }

  @Test
  public void verifyCanParseJobWithMissingEnv() throws Exception {
    final Job job = Job.newBuilder()
        .setCommand(asList("foo", "bar"))
        .setImage("foobar:4711")
        .setName("foozbarz")
        .setVersion("17")
        .build();

    final String jobJson = job.toJsonString();

    final ObjectMapper objectMapper = new ObjectMapper();
    final Map<String, Object> fields = objectMapper.readValue(
        jobJson, new TypeReference<Map<String, Object>>() {});
    fields.remove("env");
    final String modifiedJobJson = objectMapper.writeValueAsString(fields);

    final Job parsedJob = parse(modifiedJobJson, Job.class);

    assertEquals(job, parsedJob);
  }

  @Test
  public void verifyJobIsImmutable() {
    final List<String> expectedCommand = ImmutableList.of("foo");
    final Map<String, String> expectedEnv = ImmutableMap.of("e1", "1");
    final Map<String, PortMapping> expectedPorts = ImmutableMap.of("p1", PortMapping.of(1, 2));
    final Map<ServiceEndpoint, ServicePorts> expectedRegistration =
        ImmutableMap.of(ServiceEndpoint.of("foo", "tcp"), ServicePorts.of("p1"));
    final Integer expectedGracePeriod = 240;

    final List<String> mutableCommand = Lists.newArrayList(expectedCommand);
    final Map<String, String> mutableEnv = Maps.newHashMap(expectedEnv);
    final Map<String, PortMapping> mutablePorts = Maps.newHashMap(expectedPorts);
    final HashMap<ServiceEndpoint, ServicePorts> mutableRegistration =
        Maps.newHashMap(expectedRegistration);

    final Job.Builder builder = Job.newBuilder()
        .setCommand(mutableCommand)
        .setEnv(mutableEnv)
        .setPorts(mutablePorts)
        .setImage("foobar:4711")
        .setName("foozbarz")
        .setVersion("17")
        .setRegistration(mutableRegistration)
        .setGracePeriod(expectedGracePeriod);

    final Job job = builder.build();

    mutableCommand.add("bar");
    mutableEnv.put("e2", "2");
    mutablePorts.put("p2", PortMapping.of(3, 4));
    mutableRegistration.put(ServiceEndpoint.of("bar", "udp"), ServicePorts.of("p2"));

    builder.addPort("added_port", PortMapping.of(4711));
    builder.addEnv("added_env", "FOO");
    builder.addRegistration(ServiceEndpoint.of("added_reg", "added_proto"),
                            ServicePorts.of("added_port"));
    builder.setGracePeriod(480);

    assertEquals(expectedCommand, job.getCommand());
    assertEquals(expectedEnv, job.getEnv());
    assertEquals(expectedPorts, job.getPorts());
    assertEquals(expectedRegistration, job.getRegistration());
    assertEquals(expectedGracePeriod, job.getGracePeriod());
  }

  @Test
  public void testChangingPortTagsChangesJobHash() {
    final Job j = Job.newBuilder().setName("foo").setVersion("1").setImage("foobar").build();
    final Job.Builder builder = j.toBuilder();
    final Map<String, PortMapping> ports = ImmutableMap.of("add_ports1", PortMapping.of(1234),
                                                           "add_ports2", PortMapping.of(2345));
    final ImmutableMap.Builder<String, ServicePortParameters> servicePortsBuilder =
        ImmutableMap.builder();
    servicePortsBuilder.put("add_ports1", new ServicePortParameters(
        ImmutableList.of("tag1", "tag2")));
    servicePortsBuilder.put("add_ports2", new ServicePortParameters(
        ImmutableList.of("tag3", "tag4")));
    final ServicePorts servicePorts = new ServicePorts(servicePortsBuilder.build());
    final Map<ServiceEndpoint, ServicePorts> oldRegistration = ImmutableMap.of(
        ServiceEndpoint.of("add_service", "add_proto"), servicePorts);
    final Job job = builder.setPorts(ports).setRegistration(oldRegistration).build();

    final ImmutableMap.Builder<String, ServicePortParameters> newServicePortsBuilder =
        ImmutableMap.builder();
    newServicePortsBuilder.put("add_ports1", new ServicePortParameters(
        ImmutableList.of("tag1", "newtag")));
    newServicePortsBuilder.put("add_ports2", new ServicePortParameters(
        ImmutableList.of("tag3", "tag4")));
    final ServicePorts newServicePorts = new ServicePorts(newServicePortsBuilder.build());
    final Map<ServiceEndpoint, ServicePorts> newRegistration = ImmutableMap.of(
        ServiceEndpoint.of("add_service", "add_proto"), newServicePorts);
    final Job newJob = builder.setRegistration(newRegistration).build();

    assertNotEquals(job.getId().getHash(), newJob.getId().getHash());
  }
}


File: helios-services/src/main/java/com/spotify/helios/agent/TaskConfig.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.agent;

import com.google.common.base.Objects;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;

import com.spotify.docker.client.messages.ContainerConfig;
import com.spotify.docker.client.messages.HostConfig;
import com.spotify.docker.client.messages.ImageInfo;
import com.spotify.docker.client.messages.PortBinding;
import com.spotify.helios.common.descriptors.HealthCheck;
import com.spotify.helios.common.descriptors.HttpHealthCheck;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.PortMapping;
import com.spotify.helios.common.descriptors.Resources;
import com.spotify.helios.common.descriptors.ServiceEndpoint;
import com.spotify.helios.common.descriptors.ServicePortParameters;
import com.spotify.helios.common.descriptors.ServicePorts;
import com.spotify.helios.common.descriptors.TcpHealthCheck;
import com.spotify.helios.serviceregistration.ServiceRegistration;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.security.SecureRandom;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.regex.Pattern;

import static com.google.common.base.Preconditions.checkNotNull;

/**
 * Provides docker container configuration for running a task.
 */
public class TaskConfig {

  private static final Logger log = LoggerFactory.getLogger(TaskConfig.class);

  private static final Pattern CONTAINER_NAME_FORBIDDEN = Pattern.compile("[^a-zA-Z0-9_-]");

  private final String host;
  private final Map<String, Integer> ports;
  private final Job job;
  private final Map<String, String> envVars;
  private final List<ContainerDecorator> containerDecorators;
  private final String namespace;
  private final String defaultRegistrationDomain;
  private final List<String> dns;
  private final List<String> securityOpt;
  private final String networkMode;

  private TaskConfig(final Builder builder) {
    this.host = checkNotNull(builder.host, "host");
    this.ports = checkNotNull(builder.ports, "ports");
    this.job = checkNotNull(builder.job, "job");
    this.envVars = checkNotNull(builder.envVars, "envVars");
    this.containerDecorators = checkNotNull(builder.containerDecorators, "containerDecorators");
    this.namespace = checkNotNull(builder.namespace, "namespace");
    this.defaultRegistrationDomain = checkNotNull(builder.defaultRegistrationDomain,
        "defaultRegistrationDomain");
    this.dns = checkNotNull(builder.dns, "dns");
    this.securityOpt = checkNotNull(builder.securityOpt, "securityOpt");
    this.networkMode = checkNotNull(builder.networkMode, "networkMode");
  }

  /**
   * Generate a random container name.
   * @return The random container name.
   */
  public String containerName() {
    final String shortId = job.getId().toShortString();
    final String escaped = CONTAINER_NAME_FORBIDDEN.matcher(shortId).replaceAll("_");
    final String random = Integer.toHexString(new SecureRandom().nextInt());
    return namespace + "-" + escaped + "_" + random;
  }

  /**
   * Create docker container configuration for a job.
   * @param imageInfo The ImageInfo object.
   * @return The ContainerConfig object.
   */
  public ContainerConfig containerConfig(final ImageInfo imageInfo) {
    final ContainerConfig.Builder builder = ContainerConfig.builder();

    builder.image(job.getImage());
    builder.cmd(job.getCommand());
    builder.env(containerEnvStrings());
    builder.exposedPorts(containerExposedPorts());
    builder.volumes(volumes());

    for (final ContainerDecorator decorator : containerDecorators) {
      decorator.decorateContainerConfig(job, imageInfo, builder);
    }

    return builder.build();
  }

  /**
   * Get final port mappings using allocated ports.
   * @return The port mapping.
   */
  public Map<String, PortMapping> ports() {
    final ImmutableMap.Builder<String, PortMapping> builder = ImmutableMap.builder();
    for (final Map.Entry<String, PortMapping> e : job.getPorts().entrySet()) {
      final PortMapping mapping = e.getValue();
      builder.put(e.getKey(), mapping.hasExternalPort()
                              ? mapping
                              : mapping.withExternalPort(checkNotNull(ports.get(e.getKey()))));
    }
    return builder.build();
  }

  /**
   * Get environment variables for the container.
   * @return The environment variables.
   */
  public Map<String, String> containerEnv() {
    final Map<String, String> env = Maps.newHashMap(envVars);

    // Put in variables that tell the container where it's exposed
    for (Entry<String, Integer> entry : ports.entrySet()) {
      env.put("HELIOS_PORT_" + entry.getKey(), host + ":" + entry.getValue());
    }
    // Job environment variables take precedence.
    env.putAll(job.getEnv());
    return env;
  }

  public ServiceRegistration registration()
      throws InterruptedException {
    final ServiceRegistration.Builder builder = ServiceRegistration.newBuilder();

    for (final Map.Entry<ServiceEndpoint, ServicePorts> entry :
        job.getRegistration().entrySet()) {
      final ServiceEndpoint registration = entry.getKey();
      final ServicePorts servicePorts = entry.getValue();
      for (final Entry<String, ServicePortParameters> portEntry :
          servicePorts.getPorts().entrySet()) {
        final String portName = portEntry.getKey();
        final ServicePortParameters portParameters = portEntry.getValue();
        final PortMapping mapping = job.getPorts().get(portName);
        if (mapping == null) {
          log.error("no '{}' port mapped for registration: '{}'", portName, registration);
          continue;
        }
        final Integer externalPort;
        if (mapping.getExternalPort() != null) {
          // Use the statically assigned port if one is specified
          externalPort = mapping.getExternalPort();
        } else {
          // Otherwise use the dynamically allocated port
          externalPort = ports.get(portName);
        }
        if (externalPort == null) {
          log.error("no external '{}' port for registration: '{}'", portName, registration);
          continue;
        }

        builder.endpoint(registration.getName(), registration.getProtocol(), externalPort,
            fullyQualifiedRegistrationDomain(), host, portParameters.getTags(),
            endpointHealthCheck(portName));
      }
    }

    return builder.build();
  }

  /**
   * Get endpoint health check for a given port
   * @param portName The port name
   * @return An EndpointHealthCheck or null if no check exists
   */
  private ServiceRegistration.EndpointHealthCheck endpointHealthCheck(String portName) {
    if (healthCheck() instanceof HttpHealthCheck) {
      HttpHealthCheck httpHealthCheck = (HttpHealthCheck) healthCheck();
      if (portName.equals(httpHealthCheck.getPort())) {
        return ServiceRegistration.EndpointHealthCheck.newHttpCheck(httpHealthCheck.getPath());
      }
    } else if (healthCheck() instanceof TcpHealthCheck) {
      if (portName.equals(((TcpHealthCheck) healthCheck()).getPort())) {
        return ServiceRegistration.EndpointHealthCheck.newTcpCheck();
      }
    }
    return null;
  }

  public HealthCheck healthCheck() {
    return job.getHealthCheck();
  }

  /**
   * Given the registration domain in the job, and the default registration domain for the agent,
   * figure out what domain we should actually register the job in.
   * @return The full registration domain.
   */
  private String fullyQualifiedRegistrationDomain() {
    if (job.getRegistrationDomain().endsWith(".")) {
      return job.getRegistrationDomain();
    } else if ("".equals(job.getRegistrationDomain())) {
      return defaultRegistrationDomain;
    } else {
      return job.getRegistrationDomain() + "." + defaultRegistrationDomain;
    }
  }

  /**
   * Create container port exposure configuration for a job.
   * @return The exposed ports.
   */
  private Set<String> containerExposedPorts() {
    final Set<String> ports = Sets.newHashSet();
    for (final Map.Entry<String, PortMapping> entry : job.getPorts().entrySet()) {
      final PortMapping mapping = entry.getValue();
      ports.add(containerPort(mapping.getInternalPort(), mapping.getProtocol()));
    }
    return ports;
  }

  /**
   * Compute docker container environment variables.
   * @return The container environment variables.
   */
  private List<String> containerEnvStrings() {
    final Map<String, String> env = containerEnv();
    final List<String> envList = Lists.newArrayList();
    for (final Map.Entry<String, String> entry : env.entrySet()) {
      envList.add(entry.getKey() + '=' + entry.getValue());
    }
    return envList;
  }

  /**
   * Create a port binding configuration for the job.
   * @return The port bindings.
   */
  private Map<String, List<PortBinding>> portBindings() {
    final Map<String, List<PortBinding>> bindings = Maps.newHashMap();
    for (final Map.Entry<String, PortMapping> e : job.getPorts().entrySet()) {
      final PortMapping mapping = e.getValue();
      final PortBinding binding = new PortBinding();
      final Integer externalPort = mapping.getExternalPort();
      if (externalPort == null) {
        binding.hostPort(ports.get(e.getKey()).toString());
      } else {
        binding.hostPort(externalPort.toString());
      }
      final String entry = containerPort(mapping.getInternalPort(), mapping.getProtocol());
      bindings.put(entry, Collections.singletonList(binding));
    }
    return bindings;
  }

  /**
   * Create a container host configuration for the job.
   * @return The host configuration.
   */
  public HostConfig hostConfig() {
    final HostConfig.Builder builder = HostConfig.builder()
        .binds(binds())
        .portBindings(portBindings())
        .dns(dns)
        .securityOpt(securityOpt.toArray(new String[securityOpt.size()]))
        .networkMode(networkMode);

    final Resources resources = job.getResources();
    if (resources != null) {
      builder.memory(resources.getMemory());
      builder.memorySwap(resources.getMemorySwap());
      builder.cpusetCpus(resources.getCpuset());
      builder.cpuShares(resources.getCpuShares());
    }

    for (final ContainerDecorator decorator : containerDecorators) {
      decorator.decorateHostConfig(builder);
    }

    return builder.build();
  }

  /**
   * Get container volumes.
   * @return A set of container volumes.
   */
  private Set<String> volumes() {
    final ImmutableSet.Builder<String> volumes = ImmutableSet.builder();
    for (Map.Entry<String, String> entry : job.getVolumes().entrySet()) {
      final String path = entry.getKey();
      final String source = entry.getValue();
      if (Strings.isNullOrEmpty(source)) {
        volumes.add(path);
      }
    }
    return volumes.build();
  }

  /**
   * Get container bind mount volumes.
   * @return A list of container bind mount volumes.
   */
  private List<String> binds() {
    final ImmutableList.Builder<String> binds = ImmutableList.builder();
    for (Map.Entry<String, String> entry : job.getVolumes().entrySet()) {
      final String path = entry.getKey();
      final String source = entry.getValue();
      if (Strings.isNullOrEmpty(source)) {
        continue;
      }
      binds.add(source + ":" + path);
    }
    return binds.build();
  }

  /**
   * Create a docker port exposure/mapping entry.
   * @param port The port.
   * @param protocol The protocol.
   * @return A string representing the port and protocol.
   */
  private String containerPort(final int port, final String protocol) {
    return port + "/" + protocol;
  }

  public static Builder builder() {
    return new Builder();
  }

  public String containerImage() {
    return job.getImage();
  }

  public String name() {
    return job.getId().toShortString();
  }

  public static class Builder {

    private Builder() {
    }

    private String host;
    private Job job;
    private Map<String, Integer> ports = Collections.emptyMap();
    private Map<String, String> envVars = Collections.emptyMap();
    private List<ContainerDecorator> containerDecorators = Lists.newArrayList();
    private String namespace;
    private String defaultRegistrationDomain = "";
    private List<String> dns = Collections.emptyList();
    private List<String> securityOpt = Collections.emptyList();
    private String networkMode = "";

    public Builder host(final String host) {
      this.host = host;
      return this;
    }

    public Builder job(final Job job) {
      this.job = job;
      return this;
    }

    public Builder defaultRegistrationDomain(final String domain) {
      this.defaultRegistrationDomain = checkNotNull(domain, "domain");
      return this;
    }

    public Builder ports(final Map<String, Integer> ports) {
      this.ports = ports;
      return this;
    }

    public Builder envVars(final Map<String, String> envVars) {
      this.envVars = envVars;
      return this;
    }

    public Builder containerDecorators(final List<ContainerDecorator> containerDecorators) {
      this.containerDecorators = containerDecorators;
      return this;
    }

    public Builder namespace(final String namespace) {
      this.namespace = namespace;
      return this;
    }

    public Builder dns(final List<String> dns) {
      this.dns = dns;
      return this;
    }

    public Builder securityOpt(final List<String> securityOpt) {
      this.securityOpt = securityOpt;
      return this;
    }

    public Builder networkMode(final String networkMode) {
      this.networkMode = networkMode;
      return this;
    }

    public TaskConfig build() {
      return new TaskConfig(this);
    }
  }

  @Override
  public String toString() {
    return Objects.toStringHelper(this)
        .add("job", job)
        .add("host", host)
        .add("ports", ports)
        .add("envVars", envVars)
        .add("containerDecorators", containerDecorators)
        .add("defaultRegistrationDomain", defaultRegistrationDomain)
        .add("securityOpt", securityOpt)
        .add("dns", dns)
        .add("networkMode", networkMode)
        .toString();
  }
}



File: helios-system-tests/src/main/java/com/spotify/helios/system/IdMismatchJobCreateTest.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.system;

import com.spotify.helios.client.HeliosClient;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.protocol.CreateJobResponse;

import org.junit.Test;

import static com.spotify.helios.common.descriptors.Job.EMPTY_ENV;
import static com.spotify.helios.common.descriptors.Job.EMPTY_HEALTH_CHECK;
import static com.spotify.helios.common.descriptors.Job.EMPTY_NETWORK_MODE;
import static com.spotify.helios.common.descriptors.Job.EMPTY_RESOURCES;
import static com.spotify.helios.common.descriptors.Job.EMPTY_PORTS;
import static com.spotify.helios.common.descriptors.Job.EMPTY_REGISTRATION;
import static com.spotify.helios.common.descriptors.Job.EMPTY_GRACE_PERIOD;
import static com.spotify.helios.common.descriptors.Job.EMPTY_SECURITY_OPT;
import static com.spotify.helios.common.descriptors.Job.EMPTY_VOLUMES;
import static com.spotify.helios.common.descriptors.Job.EMPTY_EXPIRES;
import static com.spotify.helios.common.descriptors.Job.EMPTY_REGISTRATION_DOMAIN;
import static com.spotify.helios.common.descriptors.Job.EMPTY_CREATING_USER;
import static com.spotify.helios.common.descriptors.Job.EMPTY_TOKEN;

import static org.junit.Assert.assertEquals;

public class IdMismatchJobCreateTest extends SystemTestBase {

  @Test
  public void test() throws Exception {
    startDefaultMaster();
    final HeliosClient client = defaultClient();

    final CreateJobResponse createIdMismatch = client.createJob(
        new Job(JobId.fromString("bad:job:deadbeef"), BUSYBOX, IDLE_COMMAND,
                EMPTY_ENV, EMPTY_RESOURCES, EMPTY_PORTS, EMPTY_REGISTRATION,
                EMPTY_GRACE_PERIOD, EMPTY_VOLUMES, EMPTY_EXPIRES,
                EMPTY_REGISTRATION_DOMAIN, EMPTY_CREATING_USER, EMPTY_TOKEN,
                EMPTY_HEALTH_CHECK, EMPTY_SECURITY_OPT, EMPTY_NETWORK_MODE)).get();

    // TODO (dano): Maybe this should be ID_MISMATCH but then JobValidator must become able to
    // TODO (dano): communicate that
    assertEquals(CreateJobResponse.Status.INVALID_JOB_DEFINITION, createIdMismatch.getStatus());
  }
}


File: helios-system-tests/src/main/java/com/spotify/helios/system/SystemTestBase.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.system;

import com.google.common.base.Charsets;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Range;
import com.google.common.io.Files;
import com.google.common.util.concurrent.FutureFallback;
import com.google.common.util.concurrent.Futures;
import com.google.common.util.concurrent.ListenableFuture;
import com.google.common.util.concurrent.Service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.spotify.docker.client.ContainerNotFoundException;
import com.spotify.docker.client.DefaultDockerClient;
import com.spotify.docker.client.DockerCertificates;
import com.spotify.docker.client.DockerClient;
import com.spotify.docker.client.DockerException;
import com.spotify.docker.client.DockerRequestException;
import com.spotify.docker.client.ImageNotFoundException;
import com.spotify.docker.client.LogMessage;
import com.spotify.docker.client.LogReader;
import com.spotify.docker.client.messages.Container;
import com.spotify.docker.client.messages.ContainerConfig;
import com.spotify.docker.client.messages.ContainerCreation;
import com.spotify.docker.client.messages.ContainerInfo;
import com.spotify.docker.client.messages.HostConfig;
import com.spotify.docker.client.messages.PortBinding;
import com.spotify.helios.Polling;
import com.spotify.helios.TemporaryPorts;
import com.spotify.helios.TemporaryPorts.AllocatedPort;
import com.spotify.helios.ZooKeeperTestManager;
import com.spotify.helios.ZooKeeperTestingServerManager;
import com.spotify.helios.agent.AgentMain;
import com.spotify.helios.cli.CliMain;
import com.spotify.helios.client.HeliosClient;
import com.spotify.helios.common.Json;
import com.spotify.helios.common.descriptors.Deployment;
import com.spotify.helios.common.descriptors.DeploymentGroupStatus;
import com.spotify.helios.common.descriptors.HostStatus;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.JobStatus;
import com.spotify.helios.common.descriptors.PortMapping;
import com.spotify.helios.common.descriptors.ServiceEndpoint;
import com.spotify.helios.common.descriptors.ServicePorts;
import com.spotify.helios.common.descriptors.TaskStatus;
import com.spotify.helios.common.descriptors.ThrottleState;
import com.spotify.helios.common.protocol.DeploymentGroupStatusResponse;
import com.spotify.helios.common.protocol.JobDeleteResponse;
import com.spotify.helios.common.protocol.JobUndeployResponse;
import com.spotify.helios.master.MasterMain;
import com.spotify.helios.servicescommon.DockerHost;
import com.spotify.helios.servicescommon.coordination.CuratorClientFactory;
import com.spotify.helios.servicescommon.coordination.Paths;
import com.sun.jersey.api.client.ClientResponse;

import org.apache.curator.framework.CuratorFramework;
import org.jetbrains.annotations.NotNull;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Rule;
import org.junit.rules.ExpectedException;
import org.junit.rules.TemporaryFolder;
import org.junit.rules.TestRule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.bridge.SLF4JBridgeHandler;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.PrintStream;
import java.net.Socket;
import java.net.URI;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static com.google.common.base.CharMatcher.WHITESPACE;
import static com.google.common.base.Charsets.UTF_8;
import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Strings.isNullOrEmpty;
import static com.google.common.collect.Iterables.concat;
import static com.google.common.collect.Lists.newArrayList;
import static com.spotify.helios.common.descriptors.Job.EMPTY_ENV;
import static com.spotify.helios.common.descriptors.Job.EMPTY_EXPIRES;
import static com.spotify.helios.common.descriptors.Job.EMPTY_GRACE_PERIOD;
import static com.spotify.helios.common.descriptors.Job.EMPTY_PORTS;
import static com.spotify.helios.common.descriptors.Job.EMPTY_REGISTRATION;
import static com.spotify.helios.common.descriptors.Job.EMPTY_VOLUMES;
import static java.lang.Integer.toHexString;
import static java.util.Arrays.asList;
import static java.util.Collections.singletonList;
import static java.util.concurrent.TimeUnit.MINUTES;
import static java.util.concurrent.TimeUnit.SECONDS;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public abstract class SystemTestBase {

  private static final Logger log = LoggerFactory.getLogger(SystemTestBase.class);

  public static final int WAIT_TIMEOUT_SECONDS = 40;
  public static final int LONG_WAIT_SECONDS = 400;

  public static final String BUSYBOX = "busybox:latest";
  public static final String NGINX = "rohan/nginx-alpine:latest";
  public static final String UHTTPD = "fnichol/docker-uhttpd:latest";
  public static final String ALPINE = "onescience/alpine:latest";
  public static final String MEMCACHED = "rohan/memcached-mini:latest";
  public static final List<String> IDLE_COMMAND = asList(
      "sh", "-c", "trap 'exit 0' SIGINT SIGTERM; while :; do sleep 1; done");

  public final String testTag = "test_" + randomHexString();
  public final String testJobName = "job_" + testTag;
  public final String testJobVersion = "v" + randomHexString();
  public final String testJobNameAndVersion = testJobName + ":" + testJobVersion;

  public static final DockerHost DOCKER_HOST = DockerHost.fromEnv();

  public static final String TEST_USER = "test-user";
  public static final String TEST_HOST = "test-host";
  public static final String TEST_MASTER = "test-master";

  @Rule public final TemporaryPorts temporaryPorts = TemporaryPorts.create();

  @Rule public final TemporaryFolder temporaryFolder = new TemporaryFolder();
  @Rule public final ExpectedException exception = ExpectedException.none();
  @Rule public final TestRule watcher = new LoggingTestWatcher();

  private int masterPort;
  private int masterAdminPort;
  private String masterEndpoint;
  private boolean integrationMode;
  private Range<Integer> dockerPortRange;

  private final List<Service> services = newArrayList();
  private final List<HeliosClient> clients = Lists.newArrayList();

  private String testHost;
  private Path agentStateDirs;
  private Path masterStateDirs;
  private String masterName;

  private ZooKeeperTestManager zk;
  protected static String zooKeeperNamespace = null;
  protected final String zkClusterId = String.valueOf(ThreadLocalRandom.current().nextInt(10000));

  @BeforeClass
  public static void staticSetup() {
    SLF4JBridgeHandler.removeHandlersForRootLogger();
    SLF4JBridgeHandler.install();
  }

  @Before
  public void baseSetup() throws Exception {
    System.setProperty("user.name", TEST_USER);
    masterPort = temporaryPorts.localPort("helios master");
    masterAdminPort = temporaryPorts.localPort("helios master admin");

    String className = getClass().getName();
    if (className.endsWith("ITCase")) {
      masterEndpoint = checkNotNull(System.getenv("HELIOS_ENDPOINT"),
                                    "For integration tests, HELIOS_ENDPOINT *must* be set");
      integrationMode = true;
    } else if (className.endsWith("Test")) {
      integrationMode = false;
      masterEndpoint = "http://localhost:" + masterPort();
      // unit test
    } else {
      throw new RuntimeException("Test class' name must end in either 'Test' or 'ITCase'.");
    }

    zk = zooKeeperTestManager();
    listThreads();
    zk.ensure("/config");
    zk.ensure("/status");
    agentStateDirs = temporaryFolder.newFolder("helios-agents").toPath();
    masterStateDirs = temporaryFolder.newFolder("helios-masters").toPath();
  }

  @Before
  public void dockerSetup() throws Exception {
    final String portRange = System.getenv("DOCKER_PORT_RANGE");

    final AllocatedPort allocatedPort;
    final int probePort;
    if (portRange != null) {
      final String[] parts = portRange.split(":", 2);
      dockerPortRange = Range.closedOpen(Integer.valueOf(parts[0]),
                                         Integer.valueOf(parts[1]));
      allocatedPort = Polling.await(LONG_WAIT_SECONDS, SECONDS, new Callable<AllocatedPort>() {
        @Override
        public AllocatedPort call() throws Exception {
          final int port = ThreadLocalRandom.current().nextInt(dockerPortRange.lowerEndpoint(),
                                                               dockerPortRange.upperEndpoint());
          return temporaryPorts.tryAcquire("docker-probe", port);
        }
      });
      probePort = allocatedPort.port();
    } else {
      dockerPortRange = temporaryPorts.localPortRange("docker", 10);
      probePort = dockerPortRange().lowerEndpoint();
      allocatedPort = null;
    }

    try {
      assertDockerReachable(probePort);
    } finally {
      if (allocatedPort != null) {
        allocatedPort.release();
      }
    }
  }

  protected DockerClient getNewDockerClient() throws Exception {
    if (isNullOrEmpty(DOCKER_HOST.dockerCertPath())) {
      return new DefaultDockerClient(DOCKER_HOST.uri());
    } else {
      final Path dockerCertPath = java.nio.file.Paths.get(DOCKER_HOST.dockerCertPath());
      return new DefaultDockerClient(DOCKER_HOST.uri(), new DockerCertificates(dockerCertPath));
    }
  }

  private void assertDockerReachable(final int probePort) throws Exception {
    try (final DockerClient docker = getNewDockerClient()) {
      // Pull our base images
      try {
        docker.inspectImage(BUSYBOX);
      } catch (ImageNotFoundException e) {
        docker.pull(BUSYBOX);
      }

      try {
        docker.inspectImage(ALPINE);
      } catch (ImageNotFoundException e) {
        docker.pull(ALPINE);
      }

      // Start a container with an exposed port
      final HostConfig hostConfig = HostConfig.builder()
          .portBindings(ImmutableMap.of("4711/tcp",
                                        singletonList(PortBinding.of("0.0.0.0", probePort))))
          .build();
      final ContainerConfig config = ContainerConfig.builder()
          .image(BUSYBOX)
          .cmd("nc", "-p", "4711", "-lle", "cat")
          .exposedPorts(ImmutableSet.of("4711/tcp"))
          .hostConfig(hostConfig)
          .build();
      final ContainerCreation creation = docker.createContainer(config, testTag + "-probe");
      final String containerId = creation.id();
      docker.startContainer(containerId);

      // Wait for container to come up
      Polling.await(5, SECONDS, new Callable<Object>() {
        @Override
        public Object call() throws Exception {
          final ContainerInfo info = docker.inspectContainer(containerId);
          return info.state().running() ? true : null;
        }
      });

      log.info("Verifying that docker containers are reachable");
      try {
        Polling.awaitUnchecked(5, SECONDS, new Callable<Object>() {
          @Override
          public Object call() throws Exception {
            log.info("Probing: {}:{}", DOCKER_HOST.address(), probePort);
            try (final Socket ignored = new Socket(DOCKER_HOST.address(), probePort)) {
              return true;
            } catch (IOException e) {
              return false;
            }
          }
        });
      } catch (TimeoutException e) {
        fail("Please ensure that DOCKER_HOST is set to an address that where containers can " +
             "be reached. If docker is running in a local VM, DOCKER_HOST must be set to the " +
             "address of that VM. If docker can only be reached on a limited port range, " +
             "set the environment variable DOCKER_PORT_RANGE=start:end");
      }

      docker.killContainer(containerId);
    }
  }

  protected ZooKeeperTestManager zooKeeperTestManager() {
    return new ZooKeeperTestingServerManager(zooKeeperNamespace);
  }

  @After
  public void baseTeardown() throws Exception {
    tearDownJobs();
    for (final HeliosClient client : clients) {
      client.close();
    }
    clients.clear();

    for (Service service : services) {
      try {
        service.stopAsync();
      } catch (Exception e) {
        log.error("Uncaught exception", e);
      }
    }
    for (Service service : services) {
      try {
        service.awaitTerminated();
      } catch (Exception e) {
        log.error("Service failed", e);
      }
    }
    services.clear();

    // Clean up docker
    try (final DockerClient dockerClient = getNewDockerClient()) {
      final List<Container> containers = dockerClient.listContainers();
      for (final Container container : containers) {
        for (final String name : container.names()) {
          if (name.contains(testTag)) {
            try {
              dockerClient.killContainer(container.id());
            } catch (DockerException e) {
              e.printStackTrace();
            }
            break;
          }
        }
      }
    } catch (Exception e) {
      log.error("Docker client exception", e);
    }

    if (zk != null) {
      zk.close();
    }

    listThreads();
  }

  private void listThreads() {
    final Set<Thread> threads = Thread.getAllStackTraces().keySet();
    final Map<String, Thread> sorted = Maps.newTreeMap();
    for (final Thread t : threads) {
      final ThreadGroup tg = t.getThreadGroup();
      if (t.isAlive() && (tg == null || !tg.getName().equals("system"))) {
        sorted.put(t.getName(), t);
      }
    }
    log.info("= THREADS " + Strings.repeat("=", 70));
    for (final Thread t : sorted.values()) {
      final ThreadGroup tg = t.getThreadGroup();
      log.info("{}: \"{}\" ({}{})", t.getId(), t.getName(),
               (tg == null ? "" : tg.getName() + " "),
               (t.isDaemon() ? "daemon" : ""));
    }
    log.info(Strings.repeat("=", 80));
  }

  protected void tearDownJobs() throws InterruptedException, ExecutionException {
    if (!isIntegration()) {
      return;
    }

    if (System.getenv("ITCASE_PRESERVE_JOBS") != null) {
      return;
    }

    final List<ListenableFuture<JobUndeployResponse>> undeploys = Lists.newArrayList();
    final HeliosClient c = defaultClient();
    final Map<JobId, Job> jobs = c.jobs().get();
    for (JobId jobId : jobs.keySet()) {
      if (!jobId.toString().startsWith(testTag)) {
        continue;
      }
      final JobStatus st = c.jobStatus(jobId).get();
      final Set<String> hosts = st.getDeployments().keySet();
      for (String host : hosts) {
        log.info("Undeploying job " + jobId);
        undeploys.add(c.undeploy(jobId, host));
      }
    }
    Futures.allAsList(undeploys);

    final List<ListenableFuture<JobDeleteResponse>> deletes = Lists.newArrayList();
    for (JobId jobId : jobs.keySet()) {
      if (!jobId.toString().startsWith(testTag)) {
        continue;
      }
      log.info("Deleting job " + jobId);
      deletes.add(c.deleteJob(jobId));
    }
    Futures.allAsList(deletes);
  }

  protected boolean isIntegration() {
    return integrationMode;
  }

  protected TemporaryPorts temporaryPorts() {
    return temporaryPorts;
  }

  protected ZooKeeperTestManager zk() {
    return zk;
  }

  protected String masterEndpoint() {
    return masterEndpoint;
  }

  protected String masterName() throws InterruptedException, ExecutionException {
    if (integrationMode) {
      if (masterName == null) {
        masterName = defaultClient().listMasters().get().get(0);
      }
      return masterName;
    } else {
      return "test-master";
    }
  }

  protected HeliosClient defaultClient() {
    return client(TEST_USER, masterEndpoint());
  }

  protected HeliosClient client(final String user, final String endpoint) {
    final HeliosClient client = HeliosClient.newBuilder()
        .setUser(user)
        .setEndpoints(singletonList(URI.create(endpoint)))
        .build();
    clients.add(client);
    return client;
  }

  protected int masterPort() {
    return masterPort;
  }

  protected int masterAdminPort() {
    return masterAdminPort;
  }

  public Range<Integer> dockerPortRange() {
    return dockerPortRange;
  }

  protected String testHost() throws InterruptedException, ExecutionException {
    if (integrationMode) {
      if (testHost == null) {
        final List<String> hosts = defaultClient().listHosts().get();
        testHost = hosts.get(new SecureRandom().nextInt(hosts.size()));
      }
      return testHost;
    } else {
      return TEST_HOST;
    }
  }

  protected List<String> setupDefaultMaster(String... args) throws Exception {
    return setupDefaultMaster(0, args);
  }

  protected List<String> setupDefaultMaster(final int offset, String... args) throws Exception {
    if (isIntegration()) {
      checkArgument(args.length == 0,
                    "cannot start default master in integration test with arguments passed");
      return null;
    }

    // TODO (dano): Move this bootstrapping to something reusable
    final CuratorFramework curator = zk.curator();
    curator.newNamespaceAwareEnsurePath(Paths.configHosts()).ensure(curator.getZookeeperClient());
    curator.newNamespaceAwareEnsurePath(Paths.configJobs()).ensure(curator.getZookeeperClient());
    curator.newNamespaceAwareEnsurePath(Paths.configJobRefs()).ensure(curator.getZookeeperClient());
    curator.newNamespaceAwareEnsurePath(Paths.statusHosts()).ensure(curator.getZookeeperClient());
    curator.newNamespaceAwareEnsurePath(Paths.statusMasters()).ensure(curator.getZookeeperClient());
    curator.newNamespaceAwareEnsurePath(Paths.historyJobs()).ensure(curator.getZookeeperClient());
    curator.newNamespaceAwareEnsurePath(Paths.configId(zkClusterId))
        .ensure(curator.getZookeeperClient());

    final List<String> argsList = Lists.newArrayList(
        "-vvvv",
        "--no-log-setup",
        "--http", "http://localhost:" + (masterPort() + offset),
        "--admin=" + (masterAdminPort() + offset),
        "--domain", "",
        "--zk", zk.connectString()
    );

    final String name;
    if (asList(args).contains("--name")) {
      name = args[asList(args).indexOf("--name") + 1];
    } else {
      name = TEST_MASTER + offset;
      argsList.addAll(asList("--name", TEST_MASTER));
    }

    final String stateDir = masterStateDirs.resolve(name).toString();
    argsList.addAll(asList("--state-dir", stateDir));

    argsList.addAll(asList(args));

    return argsList;
  }

  protected MasterMain startDefaultMaster(String... args) throws Exception {
    return startDefaultMaster(0, args);
  }

  protected MasterMain startDefaultMaster(final int offset, String... args) throws Exception {
    final List<String> argsList = setupDefaultMaster(offset, args);

    if (argsList == null) {
      return null;
    }

    final MasterMain master = startMaster(argsList.toArray(new String[argsList.size()]));
    waitForMasterToConnectToZK();

    return master;
  }

  protected Map<String, MasterMain> startDefaultMasters(final int numMasters, String... args)
      throws Exception {
    final Map<String, MasterMain> masters = Maps.newHashMap();

    for (int i = 0; i < numMasters; i++) {
      final String name = TEST_MASTER + i;
      final List<String> argsList = Lists.newArrayList(args);
      argsList.addAll(asList("--name", name));
      masters.put(name, startDefaultMaster(i, argsList.toArray(new String[argsList.size()])));
    }

    return masters;
  }

  protected void waitForMasterToConnectToZK() throws Exception {
    Polling.await(WAIT_TIMEOUT_SECONDS, SECONDS, new Callable<Object>() {
      @Override
      public Object call() {
        try {
          final List<String> masters = defaultClient().listMasters().get();
          return masters != null;
        } catch (Exception e) {
          return null;
        }
      }
    });
  }

  protected void startDefaultMasterDontWaitForZK(final CuratorClientFactory curatorClientFactory,
                                                 String... args) throws Exception {
    List<String> argsList = setupDefaultMaster(args);

    if (argsList == null) {
      return;
    }

    startMaster(curatorClientFactory, argsList.toArray(new String[argsList.size()]));
  }

  protected AgentMain startDefaultAgent(final String host, final String... args)
      throws Exception {
    if (isIntegration()) {
      checkArgument(args.length == 0,
                    "cannot start default agent in integration test with arguments passed");
      return null;
    }

    final String stateDir = agentStateDirs.resolve(host).toString();
    final List<String> argsList = Lists.newArrayList("-vvvv",
                                                     "--no-log-setup",
                                                     "--no-http",
                                                     "--name", host,
                                                     "--docker=" + DOCKER_HOST,
                                                     "--zk", zk.connectString(),
                                                     "--zk-session-timeout", "100",
                                                     "--zk-connection-timeout", "100",
                                                     "--state-dir", stateDir,
                                                     "--domain", "",
                                                     "--port-range=" +
                                                     dockerPortRange.lowerEndpoint() + ":" +
                                                     dockerPortRange.upperEndpoint()
    );
    argsList.addAll(asList(args));
    return startAgent(argsList.toArray(new String[argsList.size()]));
  }

  protected MasterMain startMaster(final String... args) throws Exception {
    final MasterMain main = new MasterMain(args);
    main.startAsync().awaitRunning();
    services.add(main);
    return main;
  }

  MasterMain startMaster(final CuratorClientFactory curatorClientFactory,
                         final String... args) throws Exception {
    final MasterMain main = new MasterMain(curatorClientFactory, args);
    main.startAsync().awaitRunning();
    services.add(main);
    return main;
  }

  protected AgentMain startAgent(final String... args) throws Exception {
    final AgentMain main = new AgentMain(args);
    main.startAsync().awaitRunning();
    services.add(main);
    return main;
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command) throws Exception {
    return createJob(name, version, image, command, EMPTY_ENV, EMPTY_PORTS, EMPTY_REGISTRATION);
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command,
                            final Date expires) throws Exception {
    return createJob(name, version, image, command, EMPTY_ENV, EMPTY_PORTS, EMPTY_REGISTRATION,
                     EMPTY_GRACE_PERIOD, EMPTY_VOLUMES, expires);
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command,
                            final ImmutableMap<String, String> env)
      throws Exception {
    return createJob(name, version, image, command, env, EMPTY_PORTS, EMPTY_REGISTRATION);
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command,
                            final Map<String, String> env,
                            final Map<String, PortMapping> ports) throws Exception {
    return createJob(name, version, image, command, env, ports, EMPTY_REGISTRATION);
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command,
                            final Map<String, String> env,
                            final Map<String, PortMapping> ports,
                            final Map<ServiceEndpoint, ServicePorts> registration)
      throws Exception {
    return createJob(name, version, image, command, env, ports, registration, EMPTY_GRACE_PERIOD,
                     EMPTY_VOLUMES);
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command,
                            final Map<String, String> env,
                            final Map<String, PortMapping> ports,
                            final Map<ServiceEndpoint, ServicePorts> registration,
                            final Integer gracePeriod,
                            final Map<String, String> volumes) throws Exception {
    return createJob(name, version, image, command, env, ports, registration, gracePeriod, volumes,
        EMPTY_EXPIRES);
  }

  protected JobId createJob(final String name,
                            final String version,
                            final String image,
                            final List<String> command,
                            final Map<String, String> env,
                            final Map<String, PortMapping> ports,
                            final Map<ServiceEndpoint, ServicePorts> registration,
                            final Integer gracePeriod,
                            final Map<String, String> volumes,
                            final Date expires) throws Exception {
    return createJob(Job.newBuilder()
                         .setName(name)
                         .setVersion(version)
                         .setImage(image)
                         .setCommand(command)
                         .setEnv(env)
                         .setPorts(ports)
                         .setRegistration(registration)
                         .setGracePeriod(gracePeriod)
                         .setVolumes(volumes)
                         .setExpires(expires)
                         .build());
  }

  protected JobId createJob(final Job job) throws Exception {
    final String name = job.getId().getName();
    checkArgument(name.contains(testTag), "Job name must contain testTag to enable cleanup");

    final String serializedConfig = Json.asNormalizedString(job);
    final File configFile = temporaryFolder.newFile();
    Files.write(serializedConfig, configFile, Charsets.UTF_8);

    final List<String> args = ImmutableList.of("-q", "-f", configFile.getAbsolutePath());
    final String createOutput = cli("create", args);
    final String jobId = WHITESPACE.trimFrom(createOutput);

    return JobId.fromString(jobId);
  }

  protected void deployJob(final JobId jobId, final String host)
      throws Exception {
    final String deployOutput = cli("deploy", jobId.toString(), host);
    assertThat(deployOutput, containsString(host + ": done"));

    final String output = cli("status", "--host", host, "--json");
    final Map<JobId, JobStatus> statuses =
        Json.readUnchecked(output, new TypeReference<Map<JobId, JobStatus>>() {
        });
    assertTrue(statuses.keySet().contains(jobId));
  }

  protected void undeployJob(final JobId jobId, final String host) throws Exception {
    final String undeployOutput = cli("undeploy", jobId.toString(), host);
    assertThat(undeployOutput, containsString(host + ": done"));

    final String output = cli("status", "--host", host, "--json");
    final Map<JobId, JobStatus> statuses =
        Json.readUnchecked(output, new TypeReference<Map<JobId, JobStatus>>() {
        });
    final JobStatus status = statuses.get(jobId);
    assertTrue(status == null ||
               status.getDeployments().get(host) == null);
  }

  protected String startJob(final JobId jobId, final String host) throws Exception {
    return cli("start", jobId.toString(), host);
  }

  protected String stopJob(final JobId jobId, final String host) throws Exception {
    return cli("stop", jobId.toString(), host);
  }

  protected String deregisterHost(final String host) throws Exception {
    return cli("deregister", host, "--yes");
  }

  protected String cli(final String command, final Object... args)
      throws Exception {
    return cli(command, flatten(args));
  }

  protected String cli(final String command, final String... args)
      throws Exception {
    return cli(command, asList(args));
  }

  protected String cli(final String command, final List<String> args)
      throws Exception {
    final List<String> commands = asList(command, "-z", masterEndpoint(), "--no-log-setup");
    final List<String> allArgs = newArrayList(concat(commands, args));
    return main(allArgs).toString();
  }

  protected <T> T cliJson(final Class<T> klass, final String command, final String... args)
      throws Exception {
    return cliJson(klass, command, asList(args));
  }

  protected <T> T cliJson(final Class<T> klass, final String command, final List<String> args)
      throws Exception {
    final List<String> args0 = newArrayList("--json");
    args0.addAll(args);
    return Json.read(cli(command, args0), klass);
  }

  protected ByteArrayOutputStream main(final String... args) throws Exception {
    final ByteArrayOutputStream out = new ByteArrayOutputStream();
    final ByteArrayOutputStream err = new ByteArrayOutputStream();
    final CliMain main = new CliMain(new PrintStream(out), new PrintStream(err), args);
    main.run();
    return out;
  }

  protected ByteArrayOutputStream main(final Collection<String> args) throws Exception {
    return main(args.toArray(new String[args.size()]));
  }

  protected void awaitHostRegistered(final String name, final long timeout, final TimeUnit timeUnit)
      throws Exception {
    Polling.await(timeout, timeUnit, new Callable<Object>() {
      @Override
      public Object call() throws Exception {
        final String output = cli("hosts", "-q");
        return output.contains(name) ? true : null;
      }
    });
  }

  protected HostStatus awaitHostStatus(final String name, final HostStatus.Status status,
                                       final int timeout, final TimeUnit timeUnit)
      throws Exception {
    return Polling.await(timeout, timeUnit, new Callable<HostStatus>() {
      @Override
      public HostStatus call() throws Exception {
        final String output = cli("hosts", name, "--json");
        final Map<String, HostStatus> statuses;
        try {
          statuses = Json.read(output, new TypeReference<Map<String, HostStatus>>() {});
        } catch (IOException e) {
          return null;
        }
        final HostStatus hostStatus = statuses.get(name);
        if (hostStatus == null) {
          return null;
        }
        return (hostStatus.getStatus() == status) ? hostStatus : null;
      }
    });
  }

  protected TaskStatus awaitJobState(final HeliosClient client, final String host,
                                     final JobId jobId,
                                     final TaskStatus.State state, final int timeout,
                                     final TimeUnit timeunit) throws Exception {
    return Polling.await(timeout, timeunit, new Callable<TaskStatus>() {
      @Override
      public TaskStatus call() throws Exception {
        final HostStatus hostStatus = getOrNull(client.hostStatus(host));
        if (hostStatus == null) {
          return null;
        }
        final TaskStatus taskStatus = hostStatus.getStatuses().get(jobId);
        return (taskStatus != null && taskStatus.getState() == state) ? taskStatus
                                                                      : null;
      }
    });
  }

  protected TaskStatus awaitJobThrottle(final HeliosClient client, final String host,
                                        final JobId jobId,
                                        final ThrottleState throttled, final int timeout,
                                        final TimeUnit timeunit) throws Exception {
    return Polling.await(timeout, timeunit, new Callable<TaskStatus>() {
      @Override
      public TaskStatus call() throws Exception {
        final HostStatus hostStatus = getOrNull(client.hostStatus(host));
        if (hostStatus == null) {
          return null;
        }
        final TaskStatus taskStatus = hostStatus.getStatuses().get(jobId);
        return (taskStatus != null && taskStatus.getThrottled() == throttled) ? taskStatus : null;
      }
    });
  }

  protected void awaitHostRegistered(final HeliosClient client, final String host,
                                     final int timeout,
                                     final TimeUnit timeUnit) throws Exception {
    Polling.await(timeout, timeUnit, new Callable<HostStatus>() {
      @Override
      public HostStatus call() throws Exception {
        return getOrNull(client.hostStatus(host));
      }
    });
  }

  protected HostStatus awaitHostStatus(final HeliosClient client, final String host,
                                       final HostStatus.Status status,
                                       final int timeout,
                                       final TimeUnit timeUnit) throws Exception {
    return Polling.await(timeout, timeUnit, new Callable<HostStatus>() {
      @Override
      public HostStatus call() throws Exception {
        final HostStatus hostStatus = getOrNull(client.hostStatus(host));
        if (hostStatus == null) {
          return null;
        }
        return (hostStatus.getStatus() == status) ? hostStatus : null;
      }
    });
  }

  protected TaskStatus awaitTaskState(final JobId jobId, final String host,
                                      final TaskStatus.State state) throws Exception {
    return Polling.await(LONG_WAIT_SECONDS, SECONDS, new Callable<TaskStatus>() {
      @Override
      public TaskStatus call() throws Exception {
        final String output = cli("status", "--json", "--job", jobId.toString());
        final Map<JobId, JobStatus> statusMap;
        try {
          statusMap = Json.read(output, new TypeReference<Map<JobId, JobStatus>>() {});
        } catch (IOException e) {
          return null;
        }
        final JobStatus status = statusMap.get(jobId);
        if (status == null) {
          return null;
        }
        final TaskStatus taskStatus = status.getTaskStatuses().get(host);
        if (taskStatus == null) {
          return null;
        }
        if (taskStatus.getState() != state) {
          return null;
        }
        return taskStatus;
      }
    });
  }

  protected void awaitTaskGone(final HeliosClient client, final String host, final JobId jobId,
                               final long timeout, final TimeUnit timeunit) throws Exception {
    Polling.await(timeout, timeunit, new Callable<Boolean>() {
      @Override
      public Boolean call() throws Exception {
        final HostStatus hostStatus = getOrNull(client.hostStatus(host));
        final TaskStatus taskStatus = hostStatus.getStatuses().get(jobId);
        final Deployment deployment = hostStatus.getJobs().get(jobId);
        return taskStatus == null && deployment == null ? true : null;
      }
    });
  }

  protected DeploymentGroupStatus awaitDeploymentGroupStatus(
      final HeliosClient client,
      final String name,
      final DeploymentGroupStatus.State state)
      throws Exception {
    return Polling.await(LONG_WAIT_SECONDS, SECONDS, new Callable<DeploymentGroupStatus>() {
      @Override
      public DeploymentGroupStatus call() throws Exception {
        final DeploymentGroupStatusResponse response = getOrNull(
            client.deploymentGroupStatus(name));

        if (response != null) {
          final DeploymentGroupStatus status = response.getDeploymentGroupStatus();
          if (status.getState().equals(state)) {
            return status;
          } else if (status.getState().equals(DeploymentGroupStatus.State.FAILED)) {
            assertEquals(state, status.getState());
          }
        }

        return null;
      }
    });
  }

  protected <T> T getOrNull(final ListenableFuture<T> future)
      throws ExecutionException, InterruptedException {
    return Futures.withFallback(future, new FutureFallback<T>() {
      @Override
      public ListenableFuture<T> create(@NotNull final Throwable t) throws Exception {
        return Futures.immediateFuture(null);
      }
    }).get();
  }

  protected String readLogFully(final ClientResponse logs) throws IOException {
    final LogReader logReader = new LogReader(logs.getEntityInputStream());
    StringBuilder stringBuilder = new StringBuilder();
    LogMessage logMessage;
    while ((logMessage = logReader.nextMessage()) != null) {
      stringBuilder.append(UTF_8.decode(logMessage.content()));
    }
    logReader.close();
    return stringBuilder.toString();
  }

  protected static void removeContainer(final DockerClient dockerClient, final String containerId)
      throws Exception {
    // Work around docker sometimes failing to remove a container directly after killing it
    Polling.await(1, MINUTES, new Callable<Object>() {
      @Override
      public Object call() throws Exception {
        try {
          dockerClient.killContainer(containerId);
          dockerClient.removeContainer(containerId);
          return true;
        } catch (ContainerNotFoundException e) {
          // We're done here
          return true;
        } catch (DockerException e) {
          if ((e instanceof DockerRequestException) &&
              ((DockerRequestException) e).message().contains(
                  "Driver btrfs failed to remove root filesystem")) {
            // Workaround btrfs issue where removing containers throws an exception,
            // but succeeds anyway.
            return true;
          } else {
            return null;
          }
        }
      }
    });
  }

  protected List<Container> listContainers(final DockerClient dockerClient, final String needle)
      throws DockerException, InterruptedException {
    final List<Container> containers = dockerClient.listContainers();
    final List<Container> matches = Lists.newArrayList();
    for (final Container container : containers) {
      if (container.names() != null) {
        for (final String name : container.names()) {
          if (name.contains(needle)) {
            matches.add(container);
            break;
          }
        }
      }
    }
    return matches;
  }

  protected List<String> flatten(final Object... values) {
    final Iterable<Object> valuesList = asList(values);
    return flatten(valuesList);
  }

  protected List<String> flatten(final Iterable<?> values) {
    final List<String> list = new ArrayList<>();
    for (Object value : values) {
      if (value instanceof Iterable) {
        list.addAll(flatten((Iterable<?>) value));
      } else if (value.getClass() == String[].class) {
        list.addAll(asList((String[]) value));
      } else if (value instanceof String) {
        list.add((String) value);
      } else {
        throw new IllegalArgumentException();
      }
    }
    return list;
  }

  protected void assertJobEquals(final Job expected, final Job actual) {
    assertEquals(expected.toBuilder().setHash(actual.getId().getHash()).build(), actual);
  }

  protected static String randomHexString() {
    return toHexString(ThreadLocalRandom.current().nextInt());
  }
}


File: helios-tools/src/main/java/com/spotify/helios/cli/command/JobCreateCommand.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.cli.command;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;

import com.spotify.helios.client.HeliosClient;
import com.spotify.helios.common.JobValidator;
import com.spotify.helios.common.Json;
import com.spotify.helios.common.descriptors.ExecHealthCheck;
import com.spotify.helios.common.descriptors.HttpHealthCheck;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.PortMapping;
import com.spotify.helios.common.descriptors.ServiceEndpoint;
import com.spotify.helios.common.descriptors.ServicePorts;
import com.spotify.helios.common.descriptors.TcpHealthCheck;
import com.spotify.helios.common.protocol.CreateJobResponse;

import net.sourceforge.argparse4j.inf.Argument;
import net.sourceforge.argparse4j.inf.Namespace;
import net.sourceforge.argparse4j.inf.Subparser;

import org.joda.time.DateTime;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static com.google.common.base.Charsets.UTF_8;
import static com.google.common.base.Optional.fromNullable;
import static com.google.common.base.Strings.isNullOrEmpty;
import static com.spotify.helios.common.descriptors.PortMapping.TCP;
import static com.spotify.helios.common.descriptors.ServiceEndpoint.HTTP;
import static java.util.Arrays.asList;
import static java.util.regex.Pattern.compile;
import static net.sourceforge.argparse4j.impl.Arguments.append;
import static net.sourceforge.argparse4j.impl.Arguments.fileType;
import static net.sourceforge.argparse4j.impl.Arguments.storeTrue;

public class JobCreateCommand extends ControlCommand {

  private static final JobValidator JOB_VALIDATOR = new JobValidator();

  private final Argument fileArg;
  private final Argument templateArg;
  private final Argument quietArg;
  private final Argument idArg;
  private final Argument imageArg;
  private final Argument tokenArg;
  private final Argument envArg;
  private final Argument argsArg;
  private final Argument portArg;
  private final Argument registrationArg;
  private final Argument registrationDomainArg;
  private final Argument gracePeriodArg;
  private final Argument volumeArg;
  private final Argument expiresArg;
  private final Argument healthCheckExecArg;
  private final Argument healthCheckHttpArg;
  private final Argument healthCheckTcpArg;
  private final Argument securityOptArg;
  private final Argument networkModeArg;

  public JobCreateCommand(final Subparser parser) {
    super(parser);

    parser.help("create a job");

    fileArg = parser.addArgument("-f", "--file")
        .type(fileType().acceptSystemIn())
        .help("Job configuration file. Options specified on the command line will be merged with" +
              " the contents of this file. Cannot be used together with -t/--template.");

    templateArg = parser.addArgument("-t", "--template")
        .help("Template job id. The new job will be based on this job. Cannot be used together " +
              "with -f/--file.");

    quietArg = parser.addArgument("-q")
        .action(storeTrue())
        .help("only print job id");

    idArg = parser.addArgument("id")
        .nargs("?")
        .help("Job name:version[:hash]");

    imageArg = parser.addArgument("image")
        .nargs("?")
        .help("Container image");

    tokenArg = parser.addArgument("--token")
         .nargs("?")
         .setDefault("")
         .help("Insecure access token meant to prevent accidental changes to your job " +
               "(e.g. undeploys).");

    envArg = parser.addArgument("--env")
        .action(append())
        .setDefault(new ArrayList<String>())
        .help("Environment variables");

    portArg = parser.addArgument("-p", "--port")
        .action(append())
        .setDefault(new ArrayList<String>())
        .help("Port mapping. Specify an endpoint name and a single port (e.g. \"http=8080\") for " +
              "dynamic port mapping and a name=private:public tuple (e.g. \"http=8080:80\") for " +
              "static port mapping. E.g., foo=4711 will map the internal port 4711 of the " +
              "container to an arbitrary external port on the host. Specifying foo=4711:80 " +
              "will map internal port 4711 of the container to port 80 on the host. The " +
              "protocol will be TCP by default. For UDP, add /udp. E.g. quic=80/udp or " +
              "dns=53:53/udp. The endpoint name can be used when specifying service registration " +
              "using -r/--register.");

    registrationArg = parser.addArgument("-r", "--register")
        .action(append())
        .setDefault(new ArrayList<String>())
        .help("Service discovery registration. Specify a service name, the port name and a " +
              "protocol on the format service/protocol=port. E.g. -r website/tcp=http will " +
              "register the port named http with the protocol tcp. Protocol is optional and " +
              "default is tcp. If there is only one port mapping, this will be used by " +
              "default and it will be enough to specify only the service name, e.g. " +
              "-r wordpress.");

    registrationDomainArg = parser.addArgument("--registration-domain")
        .setDefault("")
        .help("If set, overrides the default domain in which discovery serviceregistration " +
              "occurs. What is allowed here will vary based upon the discovery service plugin " +
              "used.");

    gracePeriodArg = parser.addArgument("--grace-period")
        .type(Integer.class)
        .setDefault((Object) null)
        .help("if --grace-period is specified, Helios will unregister from service discovery and " +
              "wait the specified number of seconds before undeploying, default 0 seconds");

    volumeArg = parser.addArgument("--volume")
        .action(append())
        .setDefault(new ArrayList<String>())
        .help("Container volumes. Specify either a single path to create a data volume, " +
              "or a source path and a container path to mount a file or directory from the host. " +
              "The container path can be suffixed with \"rw\" or \"ro\" to create a read-write " +
              "or read-only volume, respectively. Format: [container-path]:[host-path]:[rw|ro].");

    argsArg = parser.addArgument("args")
        .nargs("*")
        .help("Command line arguments");

    expiresArg = parser.addArgument("-e", "--expires")
        .help("An ISO-8601 string representing the date/time when this job should expire. The " +
              "job will be undeployed from all hosts and removed at this time. E.g. " +
              "2014-06-01T12:00:00Z");

    healthCheckExecArg = parser.addArgument("--exec-check")
        .help("Run `docker exec` health check with the provided command. The service will not be " +
              "registered in service discovery until the command executes successfully in the " +
              "container, i.e. with exit code 0. E.g. --exec-check ping google.com");

    healthCheckHttpArg = parser.addArgument("--http-check")
        .help("Run HTTP health check against the provided port name and path. The service will " +
              "not be registered in service discovery until the container passes the HTTP health " +
              "check. Format: [port name]:[path].");

    healthCheckTcpArg = parser.addArgument("--tcp-check")
        .help("Run TCP health check against the provided port name. The service will not be " +
              "registered in service discovery until the container passes the TCP health check.");

    securityOptArg = parser.addArgument("--security-opt")
        .action(append())
        .setDefault(Lists.newArrayList())
        .help("Run the Docker container with a security option. " +
              "See https://docs.docker.com/reference/run/#security-configuration.");

    networkModeArg = parser.addArgument("--network-mode")
        .help("Sets the networking mode for the container. Supported values are: bridge, host, and "
              + "container:<name|id>. Docker defaults to bridge.");
  }

  @Override
  int run(final Namespace options, final HeliosClient client, final PrintStream out,
          final boolean json, final BufferedReader stdin)
      throws ExecutionException, InterruptedException, IOException {

    final boolean quiet = options.getBoolean(quietArg.getDest());

    final Job.Builder builder;

    final String id = options.getString(idArg.getDest());
    final String imageIdentifier = options.getString(imageArg.getDest());

    // Read job configuration from file

    // TODO (dano): look for e.g. Heliosfile in cwd by default?

    final String templateJobId = options.getString(templateArg.getDest());
    final File file = (File) options.get(fileArg.getDest());

    if (file != null && templateJobId != null) {
      throw new IllegalArgumentException("Please use only one of -t/--template and -f/--file");
    }

    if (file != null) {
      if (!file.exists() || !file.isFile() || !file.canRead()) {
        throw new IllegalArgumentException("Cannot read file " + file);
      }
      final byte[] bytes = Files.readAllBytes(file.toPath());
      final String config = new String(bytes, UTF_8);
      final Job job = Json.read(config, Job.class);
      builder = job.toBuilder();
     } else if (templateJobId != null) {
      final Map<JobId, Job> jobs = client.jobs(templateJobId).get();
      if (jobs.size() == 0) {
        if (!json) {
          out.printf("Unknown job: %s%n", templateJobId);
        } else {
          CreateJobResponse createJobResponse =
              new CreateJobResponse(CreateJobResponse.Status.UNKNOWN_JOB, null, null);
          out.printf(createJobResponse.toJsonString());
        }
        return 1;
      } else if (jobs.size() > 1) {
        if (!json) {
          out.printf("Ambiguous job reference: %s%n", templateJobId);
        } else {
          CreateJobResponse createJobResponse =
              new CreateJobResponse(CreateJobResponse.Status.AMBIGUOUS_JOB_REFERENCE, null, null);
          out.printf(createJobResponse.toJsonString());
        }
        return 1;
      }
      final Job template = Iterables.getOnlyElement(jobs.values());
      builder = template.toBuilder();
      if (id == null) {
        throw new IllegalArgumentException("Please specify new job name and version");
      }
    } else {
      if (id == null || imageIdentifier == null) {
        throw new IllegalArgumentException(
            "Please specify a file, or a template, or a job name, version and container image");
      }
      builder = Job.newBuilder();
    }


    // Merge job configuration options from command line arguments

    if (id != null) {
      final String[] parts = id.split(":");
      switch (parts.length) {
        case 3:
          builder.setHash(parts[2]);
          // fall through
        case 2:
          builder.setVersion(parts[1]);
          // fall through
        case 1:
          builder.setName(parts[0]);
          break;
        default:
          throw new IllegalArgumentException("Invalid Job id: " + id);
      }
    }

    if (imageIdentifier != null) {
      builder.setImage(imageIdentifier);
    }

    final List<String> command = options.getList(argsArg.getDest());
    if (command != null && !command.isEmpty()) {
      builder.setCommand(command);
    }

    final List<String> envList = options.getList(envArg.getDest());
    if (!envList.isEmpty()) {
      final Map<String, String> env = Maps.newHashMap();
      // Add environmental variables from helios job configuration file
      env.putAll(builder.getEnv());
      // Add environmental variables passed in via CLI
      // Overwrite any redundant keys to make CLI args take precedence
      for (final String s : envList) {
        final String[] parts = s.split("=", 2);
        if (parts.length != 2) {
          throw new IllegalArgumentException("Bad environment variable: " + s);
        }
        env.put(parts[0], parts[1]);
      }
      builder.setEnv(env);
    }

    // Parse port mappings
    final List<String> portSpecs = options.getList(portArg.getDest());
    final Map<String, PortMapping> explicitPorts = Maps.newHashMap();
    final Pattern portPattern = compile("(?<n>[_\\-\\w]+)=(?<i>\\d+)(:(?<e>\\d+))?(/(?<p>\\w+))?");
    for (final String spec : portSpecs) {
      final Matcher matcher = portPattern.matcher(spec);
      if (!matcher.matches()) {
        throw new IllegalArgumentException("Bad port mapping: " + spec);
      }

      final String portName = matcher.group("n");
      final int internal = Integer.parseInt(matcher.group("i"));
      final Integer external = nullOrInteger(matcher.group("e"));
      final String protocol = fromNullable(matcher.group("p")).or(TCP);

      if (explicitPorts.containsKey(portName)) {
        throw new IllegalArgumentException("Duplicate port mapping: " + portName);
      }

      explicitPorts.put(portName, PortMapping.of(internal, external, protocol));
    }

    // Merge port mappings
    final Map<String, PortMapping> ports = Maps.newHashMap();
    ports.putAll(builder.getPorts());
    ports.putAll(explicitPorts);
    builder.setPorts(ports);

    // Parse service registrations
    final Map<ServiceEndpoint, ServicePorts> explicitRegistration = Maps.newHashMap();
    final Pattern registrationPattern =
        compile("(?<srv>[a-zA-Z][_\\-\\w]+)(?:/(?<prot>\\w+))?(?:=(?<port>[_\\-\\w]+))?");
    final List<String> registrationSpecs = options.getList(registrationArg.getDest());
    for (final String spec : registrationSpecs) {
      final Matcher matcher = registrationPattern.matcher(spec);
      if (!matcher.matches()) {
        throw new IllegalArgumentException("Bad registration: " + spec);
      }

      final String service = matcher.group("srv");
      final String proto = fromNullable(matcher.group("prot")).or(HTTP);
      final String optionalPort = matcher.group("port");
      final String port;

      if (ports.size() == 0) {
        throw new IllegalArgumentException("Need port mappings for service registration.");
      }

      if (optionalPort == null) {
        if (ports.size() != 1) {
          throw new IllegalArgumentException(
              "Need exactly one port mapping for implicit service registration");
        }
        port = Iterables.getLast(ports.keySet());
      } else {
        port = optionalPort;
      }

      explicitRegistration.put(ServiceEndpoint.of(service, proto), ServicePorts.of(port));
    }

    builder.setRegistrationDomain(options.getString(registrationDomainArg.getDest()));

    // Merge service registrations
    final Map<ServiceEndpoint, ServicePorts> registration = Maps.newHashMap();
    registration.putAll(builder.getRegistration());
    registration.putAll(explicitRegistration);
    builder.setRegistration(registration);

    // Get grace period interval
    Integer gracePeriod = options.getInt(gracePeriodArg.getDest());
    if (gracePeriod != null) {
      builder.setGracePeriod(gracePeriod);
    }

    // Parse volumes
    final List<String> volumeSpecs = options.getList(volumeArg.getDest());
    for (final String spec : volumeSpecs) {
      final String[] parts = spec.split(":", 2);
      switch (parts.length) {
        // Data volume
        case 1:
          builder.addVolume(parts[0]);
          break;
        // Bind mount
        case 2:
          final String path = parts[1];
          final String source = parts[0];
          builder.addVolume(path, source);
          break;
        default:
          throw new IllegalArgumentException("Invalid volume: " + spec);
      }
    }

    // Parse expires timestamp
    final String expires = options.getString(expiresArg.getDest());
    if (expires != null) {
      // Use DateTime to parse the ISO-8601 string
      builder.setExpires(new DateTime(expires).toDate());
    }

    // Parse health check
    final String execString = options.getString(healthCheckExecArg.getDest());
    final List<String> execHealthCheck =
        (execString == null) ? null : Arrays.asList(execString.split(" "));
    final String httpHealthCheck = options.getString(healthCheckHttpArg.getDest());
    final String tcpHealthCheck = options.getString(healthCheckTcpArg.getDest());

    int numberOfHealthChecks = 0;
    for (final String c : asList(httpHealthCheck, tcpHealthCheck)) {
      if (!isNullOrEmpty(c)) {
        numberOfHealthChecks++;
      }
    }
    if (execHealthCheck != null && !execHealthCheck.isEmpty()) {
      numberOfHealthChecks++;
    }

    if (numberOfHealthChecks > 1) {
      throw new IllegalArgumentException("Only one health check may be specified.");
    }

    if (execHealthCheck != null && !execHealthCheck.isEmpty()) {
      builder.setHealthCheck(ExecHealthCheck.of(execHealthCheck));
    } else if (!isNullOrEmpty(httpHealthCheck)) {
      final String[] parts = httpHealthCheck.split(":", 2);
      if (parts.length != 2) {
        throw new IllegalArgumentException("Invalid HTTP health check: " + httpHealthCheck);
      }

      builder.setHealthCheck(HttpHealthCheck.of(parts[0], parts[1]));
    } else if (!isNullOrEmpty(tcpHealthCheck)) {
      builder.setHealthCheck(TcpHealthCheck.of(tcpHealthCheck));
    }

    builder.setSecurityOpt(options.<String>getList(securityOptArg.getDest()));

    builder.setNetworkMode(options.getString(networkModeArg.getDest()));

    builder.setToken(options.getString(tokenArg.getDest()));

    final Job job = builder.build();

    final Collection<String> errors = JOB_VALIDATOR.validate(job);
    if (!errors.isEmpty()) {
      if (!json) {
        for (String error : errors) {
          out.println(error);
        }
      } else {
        CreateJobResponse createJobResponse = new CreateJobResponse(
            CreateJobResponse.Status.INVALID_JOB_DEFINITION, ImmutableList.copyOf(errors),
            job.getId().toString());
        out.println(createJobResponse.toJsonString());
      }

      return 1;
    }

    if (!quiet && !json) {
      out.println("Creating job: " + job.toJsonString());
    }

    final CreateJobResponse status = client.createJob(job).get();
    if (status.getStatus() == CreateJobResponse.Status.OK) {
      if (!quiet && !json) {
        out.println("Done.");
      }
      if (json) {
        out.println(status.toJsonString());
      } else {
        out.println(job.getId());
      }
      return 0;
    } else {
      if (!quiet && !json) {
        out.println("Failed: " + status);
      } else if (json) {
        out.println(status.toJsonString());
      }
      return 1;
    }
  }

  private Integer nullOrInteger(final String s) {
    return s == null ? null : Integer.valueOf(s);
  }
}



File: helios-tools/src/main/java/com/spotify/helios/cli/command/JobInspectCommand.java
/*
 * Copyright (c) 2014 Spotify AB.
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package com.spotify.helios.cli.command;

import com.google.common.base.Function;
import com.google.common.base.Joiner;
import com.google.common.base.Strings;
import com.google.common.collect.Iterables;
import com.google.common.collect.Lists;
import com.google.common.collect.Ordering;

import com.spotify.helios.client.HeliosClient;
import com.spotify.helios.common.Json;
import com.spotify.helios.common.descriptors.ExecHealthCheck;
import com.spotify.helios.common.descriptors.HealthCheck;
import com.spotify.helios.common.descriptors.HttpHealthCheck;
import com.spotify.helios.common.descriptors.Job;
import com.spotify.helios.common.descriptors.JobId;
import com.spotify.helios.common.descriptors.PortMapping;
import com.spotify.helios.common.descriptors.ServicePorts;
import com.spotify.helios.common.descriptors.TcpHealthCheck;

import net.sourceforge.argparse4j.inf.Namespace;
import net.sourceforge.argparse4j.inf.Subparser;

import java.io.BufferedReader;
import java.io.PrintStream;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;

import static com.google.common.base.CharMatcher.WHITESPACE;

public class JobInspectCommand extends WildcardJobCommand {

  private static final Function<String, String> QUOTE = new Function<String, String>() {
    @Override
    public String apply(final String input) {
      return quote(input);
    }
  };

  private static final Function<PortMapping, String> FORMAT_PORTMAPPING =
      new Function<PortMapping, String>() {
        @Override
        public String apply(final PortMapping input) {
          String s = String.valueOf(input.getInternalPort());
          if (input.getExternalPort() != null) {
            s += ":" + input.getExternalPort();
          }
          if (input.getProtocol() != null) {
            s += "/" + input.getProtocol();
          }
          return s;
        }
      };

  private static final Function<ServicePorts, String> FORMAT_SERVICE_PORTS =
      new Function<ServicePorts, String>() {
        @Override
        public String apply(final ServicePorts input) {
          return Joiner.on(", ").join(Ordering.natural().sortedCopy(input.getPorts().keySet()));
        }
      };

  private static String formatHealthCheck(final HealthCheck healthCheck) {
    if (healthCheck == null) {
      return "";
    }
    String s = String.format("type: %s", String.valueOf(healthCheck.getType()));
    if (healthCheck instanceof HttpHealthCheck) {
      final HttpHealthCheck httpHealthCheck = (HttpHealthCheck) healthCheck;
      s += String.format(", port: %s, path: %s", httpHealthCheck.getPort(),
                         httpHealthCheck.getPath());
    } else if (healthCheck instanceof TcpHealthCheck) {
      final TcpHealthCheck tcpHealthCheck = (TcpHealthCheck) healthCheck;
      s += String.format(", port: %s", tcpHealthCheck.getPort());
    } else if (healthCheck instanceof ExecHealthCheck) {
      final ExecHealthCheck execHealthCheck = (ExecHealthCheck) healthCheck;
      s += String.format(", command: %s", Joiner.on(" ").join(execHealthCheck.getCommand()));
    }
    return s;
  }

  public JobInspectCommand(final Subparser parser) {
    super(parser);

    parser.help("print the configuration of a job");
  }

  @Override
  protected int runWithJobId(final Namespace options, final HeliosClient client,
                             final PrintStream out, final boolean json, final JobId jobId,
                             final BufferedReader stdin)
      throws ExecutionException, InterruptedException {

    final Map<JobId, Job> jobs = client.jobs(jobId.toString()).get();
    if (jobs.size() == 0) {
      out.printf("Unknown job: %s%n", jobId);
      return 1;
    }

    final Job job = Iterables.getOnlyElement(jobs.values());

    if (json) {
      out.println(Json.asPrettyStringUnchecked(job));
    } else {
      out.printf("Id: %s%n", job.getId());
      out.printf("Image: %s%n", job.getImage());
      out.printf("Command: %s%n", quote(job.getCommand()));
      printMap(out, "Env:   ", QUOTE, job.getEnv());
      out.printf("Health check: %s%n", formatHealthCheck(job.getHealthCheck()));
      out.printf("Grace period (seconds): %s%n", job.getGracePeriod());
      printMap(out, "Ports: ", FORMAT_PORTMAPPING, job.getPorts());
      printMap(out, "Reg: ", FORMAT_SERVICE_PORTS, job.getRegistration());
      out.printf("Security options: %s%n", job.getSecurityOpt());
      out.printf("Network mode: %s%n", job.getNetworkMode());
      out.printf("Token: %s%n", job.getToken());
      printVolumes(out, job.getVolumes());
    }

    return 0;
  }

  private <K extends Comparable<K>, V> void printMap(final PrintStream out, final String name,
                                                     final Function<V, String> transform,
                                                     final Map<K, V> values) {
    out.print(name);
    boolean first = true;
    for (final K key : Ordering.natural().sortedCopy(values.keySet())) {
      if (!first) {
        out.print(Strings.repeat(" ", name.length()));
      }
      final V value = values.get(key);
      out.printf("%s=%s%n", key, transform.apply(value));
      first = false;
    }
    if (first) {
      out.println();
    }
  }

  private void printVolumes(final PrintStream out, final Map<String, String> volumes) {
    final String prefix = "Volumes: ";
    out.print(prefix);
    boolean first = true;
    for (Map.Entry<String, String> entry : volumes.entrySet()) {
      if (!first) {
        out.print(Strings.repeat(" ", prefix.length()));
      }
      final String path = entry.getValue();
      final String source = entry.getKey();
      if (source == null) {
        out.printf("%s%n", path);
      } else {
        // Note that we're printing this in value:key order as that's the host:container:[rw|ro]
        // order used by docker and the helios create command.
        out.printf("%s:%s%n", path, source);
      }
      first = false;
    }
    if (first) {
      out.println();
    }
  }

  private static String quote(final String s) {
    if (s == null) {
      return "";
    }
    return WHITESPACE.matchesAnyOf(s)
           ? '"' + s + '"'
           : s;
  }

  private static List<String> quote(final List<String> ss) {
    final List<String> output = Lists.newArrayList();
    for (String s : ss) {
      output.add(quote(s));
    }
    return output;
  }
}
