Refactoring Types: ['Move Class']
in/java/org/sonar/server/computation/measure/BatchMeasureToMeasure.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.computation.measure;

import com.google.common.base.Optional;
import java.util.Objects;
import javax.annotation.Nullable;
import org.sonar.batch.protocol.output.BatchReport;
import org.sonar.server.computation.metric.Metric;

public class BatchMeasureToMeasure {

  public Optional<Measure> toMeasure(@Nullable BatchReport.Measure batchMeasure, Metric metric) {
    Objects.requireNonNull(metric);
    if (batchMeasure == null) {
      return Optional.absent();
    }

    String data = batchMeasure.hasStringValue() ? batchMeasure.getStringValue() : null;
    switch (metric.getType().getValueType()) {
      case INT:
        return toIntegerMeasure(batchMeasure, data);
      case LONG:
        return toLongMeasure(batchMeasure, data);
      case DOUBLE:
        return toDoubleMeasure(batchMeasure, data);
      case BOOLEAN:
        return toBooleanMeasure(batchMeasure, data);
      case STRING:
        return toStringMeasure(batchMeasure);
      case LEVEL:
        return toLevelMeasure(batchMeasure);
      case NO_VALUE:
        return toNoValueMeasure(batchMeasure);
      default:
        throw new IllegalArgumentException("Unsupported Measure.ValueType " + metric.getType().getValueType());
    }
  }

  private static Optional<Measure> toIntegerMeasure(BatchReport.Measure batchMeasure, @Nullable String data) {
    if (!batchMeasure.hasIntValue()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    return toMeasure(MeasureImpl.create(batchMeasure.getIntValue(), data), batchMeasure);
  }

  private static Optional<Measure> toLongMeasure(BatchReport.Measure batchMeasure, @Nullable String data) {
    if (!batchMeasure.hasLongValue()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    return toMeasure(MeasureImpl.create(batchMeasure.getLongValue(), data), batchMeasure);
  }

  private static Optional<Measure> toDoubleMeasure(BatchReport.Measure batchMeasure, @Nullable String data) {
    if (!batchMeasure.hasDoubleValue()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    return toMeasure(MeasureImpl.create(batchMeasure.getDoubleValue(), data), batchMeasure);
  }

  private static Optional<Measure> toBooleanMeasure(BatchReport.Measure batchMeasure, @Nullable String data) {
    if (!batchMeasure.hasBooleanValue()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    return toMeasure(MeasureImpl.create(batchMeasure.getBooleanValue(), data), batchMeasure);
  }

  private static Optional<Measure> toStringMeasure(BatchReport.Measure batchMeasure) {
    if (!batchMeasure.hasStringValue()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    return toMeasure(MeasureImpl.create(batchMeasure.getStringValue()), batchMeasure);
  }
  
  private static Optional<Measure> toLevelMeasure(BatchReport.Measure batchMeasure) {
    if (!batchMeasure.hasStringValue()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    Optional<Measure.Level> level = Measure.Level.toLevel(batchMeasure.getStringValue());
    if (!level.isPresent()) {
      return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
    }
    return toMeasure(MeasureImpl.create(level.get()), batchMeasure);
  }

  private static Optional<Measure> toNoValueMeasure(BatchReport.Measure batchMeasure) {
    return toMeasure(MeasureImpl.createNoValue(), batchMeasure);
  }

  private static Optional<Measure> toMeasure(MeasureImpl measure, BatchReport.Measure batchMeasure) {
    if (batchMeasure.hasAlertStatus() && !measure.hasQualityGateStatus()) {
      Optional<Measure.Level> qualityGateStatus = Measure.Level.toLevel(batchMeasure.getAlertStatus());
      if (qualityGateStatus.isPresent()) {
        String text = batchMeasure.hasAlertText() ? batchMeasure.getAlertText() : null;
        measure.setQualityGateStatus(new Measure.QualityGateStatus(qualityGateStatus.get(), text));
      }
    }
    return Optional.of((Measure) measure);
  }

}


File: server/sonar-server/src/main/java/org/sonar/server/computation/measure/Measure.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.computation.measure;

import com.google.common.base.Objects;
import com.google.common.base.Optional;
import javax.annotation.CheckForNull;
import javax.annotation.Nullable;
import javax.annotation.concurrent.Immutable;

import static java.util.Objects.requireNonNull;

public interface Measure {

  enum ValueType {
    NO_VALUE, BOOLEAN, INT, LONG, DOUBLE, STRING, LEVEL
  }

  enum Level {
    OK("Green"),
    WARN("Orange"),
    ERROR("Red");

    private final String colorName;

    Level(String colorName) {
      this.colorName = colorName;
    }

    public String getColorName() {
      return colorName;
    }

    public static Optional<Level> toLevel(@Nullable String level) {
      if (level == null) {
        return Optional.absent();
      }
      try {
        return Optional.of(Level.valueOf(level));
      } catch (IllegalArgumentException e) {
        return Optional.absent();
      }
    }
  }

  /**
   * A QualityGate status has a level and an optional describing text.
   */
  @Immutable
  final class QualityGateStatus {
    private final Level status;
    @CheckForNull
    private final String text;

    /**
     * Creates a QualityGateStatus without a text.
     */
    public QualityGateStatus(Level status) {
      this(status, null);
    }

    /**
     * Creates a QualityGateStatus with a optional text.
     */
    public QualityGateStatus(Level status, @Nullable String text) {
      this.status = requireNonNull(status);
      this.text = text;
    }

    public Level getStatus() {
      return status;
    }

    @CheckForNull
    public String getText() {
      return text;
    }

    @Override
    public String toString() {
      return Objects.toStringHelper(this)
          .add("status", status)
          .add("text", text)
          .toString();
    }
  }

  /**
   * The type of value stored in the measure.
   */
  ValueType getValueType();

  /**
   * The value of this measure as a boolean if the type is {@link Measure.ValueType#BOOLEAN}.
   *
   * @throws IllegalStateException if the value type of the measure is not {@link Measure.ValueType#BOOLEAN}
   */
  boolean getBooleanValue();

  /**
   * The value of this measure as a int if the type is {@link Measure.ValueType#INT}.
   *
   * @throws IllegalStateException if the value type of the measure is not {@link Measure.ValueType#INT}
   */
  int getIntValue();

  /**
   * The value of this measure as a long if the type is {@link Measure.ValueType#LONG}.
   *
   * @throws IllegalStateException if the value type of the measure is not {@link Measure.ValueType#LONG}
   */
  long getLongValue();

  /**
   * The value of this measure as a double if the type is {@link Measure.ValueType#DOUBLE}.
   *
   * @throws IllegalStateException if the value type of the measure is not {@link Measure.ValueType#DOUBLE}
   */
  double getDoubleValue();

  /**
   * The value of this measure as a String if the type is {@link Measure.ValueType#STRING}.
   *
   * @throws IllegalStateException if the value type of the measure is not {@link Measure.ValueType#STRING}
   */
  String getStringValue();

  /**
   * The value of this measure as a Level if the type is {@link Measure.ValueType#LEVEL}.
   *
   * @throws IllegalStateException if the value type of the measure is not {@link Measure.ValueType#LEVEL}
   */
  Level getLevelValue();

  /**
   * The data of this measure if it exists.
   * <p>
   * If the measure type is {@link Measure.ValueType#STRING}, the value returned by this function is the same as {@link #getStringValue()}.
   * </p>
   */
  @CheckForNull
  String getData();

  /**
   * Any Measure, which ever is its value type, can have a QualityGate status.
   */
  boolean hasQualityGateStatus();

  /**
   * The QualityGate status for this measure.
   * <strong>Don't call this method unless you've checked the result of {@link #hasQualityGateStatus()} first</strong>
   *
   * @throws IllegalStateException if the measure has no QualityGate status
   */
  QualityGateStatus getQualityGateStatus();

}


File: server/sonar-server/src/main/java/org/sonar/server/computation/measure/MeasureDtoToMeasure.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.computation.measure;

import com.google.common.base.Optional;
import java.util.Objects;
import javax.annotation.Nullable;
import org.sonar.core.measure.db.MeasureDto;
import org.sonar.server.computation.metric.Metric;

import static org.sonar.server.computation.measure.Measure.Level.toLevel;

public class MeasureDtoToMeasure {

  public Optional<Measure> toMeasure(@Nullable MeasureDto measureDto, Metric metric) {
    Objects.requireNonNull(metric);
    if (measureDto == null) {
      return Optional.absent();
    }

    Double value = measureDto.getValue();
    String data = measureDto.getData();
    switch (metric.getType().getValueType()) {
      case INT:
        return toIntegerMeasure(measureDto, value, data);
      case LONG:
        return toLongMeasure(measureDto, value, data);
      case DOUBLE:
        return toDoubleMeasure(measureDto, value, data);
      case BOOLEAN:
        return toBooleanMeasure(measureDto, value, data);
      case STRING:
        return toStringMeasure(measureDto, data);
      case LEVEL:
        return toLevelMeasure(measureDto, data);
      case NO_VALUE:
        return toNoValueMeasure(measureDto);
      default:
        throw new IllegalArgumentException("Unsupported Measure.ValueType " + metric.getType().getValueType());
    }
  }

  private static Optional<Measure> toIntegerMeasure(MeasureDto measureDto, @Nullable Double value, String data) {
    if (value == null) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    return toMeasure(MeasureImpl.create(value.intValue(), data), measureDto);
  }

  private static Optional<Measure> toLongMeasure(MeasureDto measureDto, @Nullable Double value, String data) {
    if (value == null) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    return toMeasure(MeasureImpl.create(value.longValue(), data), measureDto);
  }

  private static Optional<Measure> toDoubleMeasure(MeasureDto measureDto, @Nullable Double value, String data) {
    if (value == null) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    return toMeasure(MeasureImpl.create(value.doubleValue(), data), measureDto);
  }

  private static Optional<Measure> toBooleanMeasure(MeasureDto measureDto, @Nullable Double value, String data) {
    if (value == null) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    return toMeasure(MeasureImpl.create(value == 1.0d, data), measureDto);
  }

  private static Optional<Measure> toStringMeasure(MeasureDto measureDto, @Nullable String data) {
    if (data == null) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    return toMeasure(MeasureImpl.create(data), measureDto);
  }

  private static Optional<Measure> toLevelMeasure(MeasureDto measureDto, @Nullable String data) {
    if (data == null) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    Optional<Measure.Level> level = toLevel(data);
    if (!level.isPresent()) {
      return toMeasure(MeasureImpl.createNoValue(), measureDto);
    }
    return toMeasure(MeasureImpl.create(level.get()), measureDto);
  }

  private static Optional<Measure> toNoValueMeasure(MeasureDto measureDto) {
    return toMeasure(MeasureImpl.createNoValue(), measureDto);
  }

  private static Optional<Measure> toMeasure(MeasureImpl measure, MeasureDto measureDto) {
    if (measureDto.getAlertStatus() != null && !measure.hasQualityGateStatus()) {
      Optional<Measure.Level> qualityGateStatus = toLevel(measureDto.getAlertStatus());
      if (qualityGateStatus.isPresent()) {
        measure.setQualityGateStatus(new Measure.QualityGateStatus(qualityGateStatus.get(), measureDto.getAlertText()));
      }
    }

    return Optional.of((Measure) measure);
  }

}


File: server/sonar-server/src/main/java/org/sonar/server/computation/step/QualityGateEventsStep.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.computation.step;

import com.google.common.base.Optional;
import javax.annotation.Nullable;
import org.sonar.api.measures.CoreMetrics;
import org.sonar.api.notifications.Notification;
import org.sonar.api.utils.log.Logger;
import org.sonar.api.utils.log.Loggers;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.DepthTraversalTypeAwareVisitor;
import org.sonar.server.computation.component.TreeRootHolder;
import org.sonar.server.computation.event.Event;
import org.sonar.server.computation.event.EventRepository;
import org.sonar.server.computation.measure.Measure;
import org.sonar.server.computation.measure.MeasureRepository;
import org.sonar.server.computation.metric.Metric;
import org.sonar.server.computation.metric.MetricRepository;
import org.sonar.server.notification.NotificationManager;

public class QualityGateEventsStep implements ComputationStep {
  private static final Logger LOGGER = Loggers.get(QualityGateEventsStep.class);

  private final TreeRootHolder treeRootHolder;
  private final MetricRepository metricRepository;
  private final MeasureRepository measureRepository;
  private final EventRepository eventRepository;
  private final NotificationManager notificationManager;

  public QualityGateEventsStep(TreeRootHolder treeRootHolder,
    MetricRepository metricRepository, MeasureRepository measureRepository, EventRepository eventRepository,
    NotificationManager notificationManager) {
    this.treeRootHolder = treeRootHolder;
    this.metricRepository = metricRepository;
    this.measureRepository = measureRepository;
    this.eventRepository = eventRepository;
    this.notificationManager = notificationManager;
  }

  @Override
  public void execute() {
    new DepthTraversalTypeAwareVisitor(Component.Type.PROJECT, DepthTraversalTypeAwareVisitor.Order.PRE_ORDER) {
      @Override
      public void visitProject(Component project) {
        executeForProject(project);
      }
    }.visit(treeRootHolder.getRoot());
  }

  private void executeForProject(Component project) {
    Metric metric = metricRepository.getByKey(CoreMetrics.ALERT_STATUS_KEY);
    Optional<Measure> rawStatus = measureRepository.getRawMeasure(project, metric);
    if (!rawStatus.isPresent() || !rawStatus.get().hasQualityGateStatus()) {
      return;
    }

    checkQualityGateStatusChange(project, metric, rawStatus.get().getQualityGateStatus());
  }

  private void checkQualityGateStatusChange(Component project, Metric metric, Measure.QualityGateStatus rawStatus) {
    Optional<Measure> baseMeasure = measureRepository.getBaseMeasure(project, metric);
    if (!baseMeasure.isPresent()) {
      checkNewQualityGate(project, rawStatus);
      return;
    }

    if (!baseMeasure.get().hasQualityGateStatus()) {
      LOGGER.warn(String.format("Previous alterStatus for project %s is not a supported value. Can not compute Quality Gate event", project.getKey()));
      checkNewQualityGate(project, rawStatus);
      return;
    }
    Measure.QualityGateStatus baseStatus = baseMeasure.get().getQualityGateStatus();

    if (baseStatus.getStatus() != rawStatus.getStatus()) {
      // The QualityGate status has changed
      String label = String.format("%s (was %s)", rawStatus.getStatus().getColorName(), baseStatus.getStatus().getColorName());
      createEvent(project, label, rawStatus.getText());
      boolean isNewKo = (rawStatus.getStatus() == Measure.Level.OK);
      notifyUsers(project, label, rawStatus, isNewKo);
    }
  }

  private void checkNewQualityGate(Component project, Measure.QualityGateStatus rawStatus) {
    if (rawStatus.getStatus() != Measure.Level.OK) {
      // There were no defined alerts before, so this one is a new one
      createEvent(project, rawStatus.getStatus().getColorName(), rawStatus.getText());
      notifyUsers(project, rawStatus.getStatus().getColorName(), rawStatus, true);
    }
  }

  /**
   * @param label "Red (was Orange)"
   * @param rawStatus OK, WARN or ERROR + optional text
   */
  private void notifyUsers(Component project, String label, Measure.QualityGateStatus rawStatus, boolean isNewAlert) {
    Notification notification = new Notification("alerts")
      .setDefaultMessage(String.format("Alert on %s: %s", project.getName(), label))
      .setFieldValue("projectName", project.getName())
      .setFieldValue("projectKey", project.getKey())
      .setFieldValue("projectUuid", project.getUuid())
      .setFieldValue("alertName", label)
      .setFieldValue("alertText", rawStatus.getText())
      .setFieldValue("alertLevel", rawStatus.getStatus().toString())
      .setFieldValue("isNewAlert", Boolean.toString(isNewAlert));
    notificationManager.scheduleForSending(notification);
  }

  private void createEvent(Component project, String name, @Nullable String description) {
    eventRepository.add(project, Event.createAlert(name, null, description));
  }

  @Override
  public String getDescription() {
    return "Generate Quality Gate Events";
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/computation/measure/MeasureImplTest.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.computation.measure;

import com.google.common.base.Function;
import com.google.common.base.Predicate;
import com.google.common.collect.ImmutableList;
import com.tngtech.java.junit.dataprovider.DataProvider;
import com.tngtech.java.junit.dataprovider.DataProviderRunner;
import com.tngtech.java.junit.dataprovider.UseDataProvider;
import java.util.List;
import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.sonar.server.computation.measure.Measure.ValueType;

import static com.google.common.collect.FluentIterable.from;
import static org.assertj.core.api.Assertions.assertThat;

@RunWith(DataProviderRunner.class)
public class MeasureImplTest {

  private static final MeasureImpl INT_MEASURE = MeasureImpl.create((int) 1, null);
  private static final MeasureImpl LONG_MEASURE = MeasureImpl.create(1l, null);
  private static final MeasureImpl DOUBLE_MEASURE = MeasureImpl.create(1d, null);
  private static final MeasureImpl STRING_MEASURE = MeasureImpl.create("some_sT ring");
  private static final MeasureImpl TRUE_MEASURE = MeasureImpl.create(true, null);
  private static final MeasureImpl FALSE_MEASURE = MeasureImpl.create(false, null);
  private static final MeasureImpl LEVEL_MEASURE = MeasureImpl.create(Measure.Level.OK);
  private static final MeasureImpl NO_VALUE_MEASURE = MeasureImpl.createNoValue();

  private static final List<MeasureImpl> MEASURES = ImmutableList.of(
    INT_MEASURE, LONG_MEASURE, DOUBLE_MEASURE, STRING_MEASURE, TRUE_MEASURE, FALSE_MEASURE, NO_VALUE_MEASURE, LEVEL_MEASURE
    );

  @Test(expected = NullPointerException.class)
  public void create_from_String_throws_NPE_if_arg_is_null() {
    MeasureImpl.create((String) null);
  }

  @DataProvider
  public static Object[][] all_but_INT_MEASURE() {
    return getMeasuresExcept(ValueType.INT);
  }

  @DataProvider
  public static Object[][] all_but_LONG_MEASURE() {
    return getMeasuresExcept(ValueType.LONG);
  }

  @DataProvider
  public static Object[][] all_but_DOUBLE_MEASURE() {
    return getMeasuresExcept(ValueType.DOUBLE);
  }

  @DataProvider
  public static Object[][] all_but_BOOLEAN_MEASURE() {
    return getMeasuresExcept(ValueType.BOOLEAN);
  }

  @DataProvider
  public static Object[][] all_but_STRING_MEASURE() {
    return getMeasuresExcept(ValueType.STRING);
  }

  @DataProvider
  public static Object[][] all_but_LEVEL_MEASURE() {
    return getMeasuresExcept(ValueType.LEVEL);
  }

  @DataProvider
  public static Object[][] all() {
    return from(MEASURES).transform(WrapInArray.INSTANCE).toArray(MeasureImpl[].class);
  }

  private static MeasureImpl[][] getMeasuresExcept(final ValueType valueType) {
    return from(MEASURES)
      .filter(new Predicate<MeasureImpl>() {
        @Override
        public boolean apply(@Nonnull MeasureImpl input) {
            return input.getValueType() != valueType;
        }
      }).transform(WrapInArray.INSTANCE)
        .toArray(MeasureImpl[].class);
  }

  @Test
  public void create_from_int_has_INT_value_type() {
    assertThat(INT_MEASURE.getValueType()).isEqualTo(ValueType.INT);
  }

  @Test
  public void create_from_long_has_LONG_value_type() {
    assertThat(LONG_MEASURE.getValueType()).isEqualTo(ValueType.LONG);
  }

  @Test
  public void create_from_double_has_DOUBLE_value_type() {
    assertThat(DOUBLE_MEASURE.getValueType()).isEqualTo(ValueType.DOUBLE);
  }

  @Test
  public void create_from_boolean_has_BOOLEAN_value_type() {
    assertThat(TRUE_MEASURE.getValueType()).isEqualTo(ValueType.BOOLEAN);
    assertThat(FALSE_MEASURE.getValueType()).isEqualTo(ValueType.BOOLEAN);
  }

  @Test
  public void create_from_String_has_STRING_value_type() {
    assertThat(STRING_MEASURE.getValueType()).isEqualTo(ValueType.STRING);
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all_but_INT_MEASURE")
  public void getIntValue_throws_ISE_for_all_value_types_except_INT(Measure measure) {
    measure.getIntValue();
  }

  @Test
  public void getIntValue_returns_value_for_INT_value_type() {
    assertThat(INT_MEASURE.getIntValue()).isEqualTo(1);
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all_but_LONG_MEASURE")
  public void getLongValue_throws_ISE_for_all_value_types_except_LONG(Measure measure) {
    measure.getLongValue();
  }

  @Test
  public void getLongValue_returns_value_for_LONG_value_type() {
    assertThat(LONG_MEASURE.getLongValue()).isEqualTo(1);
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all_but_DOUBLE_MEASURE")
  public void getDoubleValue_throws_ISE_for_all_value_types_except_DOUBLE(Measure measure) {
    measure.getDoubleValue();
  }

  @Test
  public void getDoubleValue_returns_value_for_DOUBLE_value_type() {
    assertThat(DOUBLE_MEASURE.getDoubleValue()).isEqualTo(1d);
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all_but_BOOLEAN_MEASURE")
  public void getBooleanValue_throws_ISE_for_all_value_types_except_BOOLEAN(Measure measure) {
    measure.getBooleanValue();
  }

  @Test
  public void getBooleanValue_returns_value_for_BOOLEAN_value_type() {
    assertThat(TRUE_MEASURE.getBooleanValue()).isTrue();
    assertThat(FALSE_MEASURE.getBooleanValue()).isFalse();
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all_but_STRING_MEASURE")
  public void getStringValue_throws_ISE_for_all_value_types_except_STRING(Measure measure) {
    measure.getStringValue();
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all_but_LEVEL_MEASURE")
  public void getLevelValue_throws_ISE_for_all_value_types_except_LEVEL(Measure measure) {
    measure.getLevelValue();
  }

  @Test
  public void getData_returns_null_for_NO_VALUE_value_type() {
    assertThat(NO_VALUE_MEASURE.getData()).isNull();
  }

  @Test
  @UseDataProvider("all_but_STRING_MEASURE")
  public void getData_returns_null_for_all_value_types_but_STRING_when_not_set(Measure measure) {
    assertThat(measure.getData()).isNull();
  }

  @Test
  public void getData_returns_value_for_STRING_value_type() {
    assertThat(STRING_MEASURE.getData()).isEqualTo(STRING_MEASURE.getStringValue());
  }

  @Test
  @UseDataProvider("all")
  public void hasAlertStatus_returns_false_for_all_value_types_when_not_set(Measure measure) {
    assertThat(measure.hasQualityGateStatus()).isFalse();
  }

  @Test(expected = IllegalStateException.class)
  @UseDataProvider("all")
  public void getAlertStatus_throws_ISE_for_all_value_types_when_not_set(Measure measure) {
    measure.getQualityGateStatus();
  }

  @Test
  public void getAlertStatus_returns_argument_from_setAlertStatus() {
    Measure.QualityGateStatus someStatus = new Measure.QualityGateStatus(Measure.Level.OK);

    assertThat(MeasureImpl.create(true, null).setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
    assertThat(MeasureImpl.create(false, null).setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
    assertThat(MeasureImpl.create((int) 1, null).setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
    assertThat(MeasureImpl.create((long) 1, null).setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
    assertThat(MeasureImpl.create((double) 1, null).setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
    assertThat(MeasureImpl.create("str").setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
    assertThat(MeasureImpl.create(Measure.Level.OK).setQualityGateStatus(someStatus).getQualityGateStatus()).isEqualTo(someStatus);
  }

  @Test(expected = NullPointerException.class)
  @UseDataProvider("all")
  public void setAlertStatus_throws_NPE_if_arg_is_null(MeasureImpl measure) {
    measure.setQualityGateStatus(null);
  }

  @Test
  public void getData_returns_argument_from_factory_method() {
    String someData = "lololool";

    assertThat(MeasureImpl.create(true, someData).getData()).isEqualTo(someData);
    assertThat(MeasureImpl.create(false, someData).getData()).isEqualTo(someData);
    assertThat(MeasureImpl.create((int) 1, someData).getData()).isEqualTo(someData);
    assertThat(MeasureImpl.create((long) 1, someData).getData()).isEqualTo(someData);
    assertThat(MeasureImpl.create((double) 1, someData).getData()).isEqualTo(someData);
  }

  @Test
  public void measure_of_value_type_LEVEL_has_no_data() {
    assertThat(LEVEL_MEASURE.getData()).isNull();
  }

  private enum WrapInArray implements Function<MeasureImpl, MeasureImpl[]> {
    INSTANCE;

    @Nullable
    @Override
    public MeasureImpl[] apply(@Nonnull MeasureImpl input) {
      return new MeasureImpl[] {input};
    }
  }
}


File: server/sonar-server/src/test/java/org/sonar/server/computation/step/QualityGateEventsStepTest.java
/*
 * SonarQube, open source software quality management tool.
 * Copyright (C) 2008-2014 SonarSource
 * mailto:contact AT sonarsource DOT com
 *
 * SonarQube is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * SonarQube is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */
package org.sonar.server.computation.step;

import com.google.common.base.Optional;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.sonar.api.notifications.Notification;
import org.sonar.server.computation.batch.TreeRootHolderRule;
import org.sonar.server.computation.component.Component;
import org.sonar.server.computation.component.DumbComponent;
import org.sonar.server.computation.event.Event;
import org.sonar.server.computation.event.EventRepository;
import org.sonar.server.computation.measure.Measure;
import org.sonar.server.computation.measure.MeasureImpl;
import org.sonar.server.computation.measure.MeasureRepository;
import org.sonar.server.computation.metric.Metric;
import org.sonar.server.computation.metric.MetricRepository;
import org.sonar.server.notification.NotificationManager;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Matchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoMoreInteractions;
import static org.mockito.Mockito.when;
import static org.sonar.api.measures.CoreMetrics.ALERT_STATUS_KEY;
import static org.sonar.server.computation.measure.Measure.Level.ERROR;
import static org.sonar.server.computation.measure.Measure.Level.OK;
import static org.sonar.server.computation.measure.Measure.Level.WARN;

public class QualityGateEventsStepTest {
  private static final DumbComponent PROJECT_COMPONENT = DumbComponent.builder(Component.Type.PROJECT, 1).setUuid("uuid 1").setKey("key 1")
    .addChildren(DumbComponent.builder(Component.Type.MODULE, 2).build())
    .build();
  private static final String INVALID_ALERT_STATUS = "trololo";
  private static final String ALERT_TEXT = "alert text";
  private static final Measure.QualityGateStatus OK_QUALITY_GATE_STATUS = new Measure.QualityGateStatus(OK, ALERT_TEXT);
  private static final Measure.QualityGateStatus WARN_QUALITY_GATE_STATUS = new Measure.QualityGateStatus(WARN, ALERT_TEXT);
  private static final Measure.QualityGateStatus ERROR_QUALITY_GATE_STATUS = new Measure.QualityGateStatus(ERROR, ALERT_TEXT);

  @Rule
  public TreeRootHolderRule treeRootHolder = new TreeRootHolderRule();

  private ArgumentCaptor<Event> eventArgumentCaptor = ArgumentCaptor.forClass(Event.class);
  private ArgumentCaptor<Notification> notificationArgumentCaptor = ArgumentCaptor.forClass(Notification.class);

  private Metric alertStatusMetric = mock(Metric.class);

  private MetricRepository metricRepository = mock(MetricRepository.class);
  private MeasureRepository measureRepository = mock(MeasureRepository.class);
  private EventRepository eventRepository = mock(EventRepository.class);
  private NotificationManager notificationManager = mock(NotificationManager.class);
  private QualityGateEventsStep underTest = new QualityGateEventsStep(treeRootHolder, metricRepository, measureRepository, eventRepository, notificationManager);

  @Before
  public void setUp() throws Exception {
    when(metricRepository.getByKey(ALERT_STATUS_KEY)).thenReturn(alertStatusMetric);
    treeRootHolder.setRoot(PROJECT_COMPONENT);
  }

  @Test
  public void no_event_if_no_raw_ALERT_STATUS_measure() {
    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(Optional.<Measure>absent());

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verifyNoMoreInteractions(measureRepository, eventRepository);
  }

  @Test
  public void no_event_created_if_raw_ALERT_STATUS_measure_is_null() {
    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue()));

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verifyNoMoreInteractions(measureRepository, eventRepository);
  }

  private static Optional<Measure> of(MeasureImpl measure) {
    return Optional.of((Measure) measure);
  }

  @Test
  public void no_event_created_if_raw_ALERT_STATUS_measure_is_unsupported_value() {
    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.create(INVALID_ALERT_STATUS)));

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verifyNoMoreInteractions(measureRepository, eventRepository);
  }

  @Test
  public void no_event_created_if_no_base_ALERT_STATUS_and_raw_is_OK() {
    Measure.QualityGateStatus someQGStatus = new Measure.QualityGateStatus(Measure.Level.OK);

    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue().setQualityGateStatus(someQGStatus)));
    when(measureRepository.getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue()));

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verify(measureRepository).getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verifyNoMoreInteractions(measureRepository, eventRepository);
  }

  @Test
  public void event_created_if_no_base_ALERT_STATUS_and_raw_is_WARN() {
    verify_event_created_if_no_base_ALERT_STATUS_measure(WARN, "Orange");
  }

  @Test
  public void event_created_if_base_ALERT_STATUS_and_raw_is_ERROR() {
    verify_event_created_if_no_base_ALERT_STATUS_measure(ERROR, "Red");
  }

  @Test
  public void event_created_if_base_ALERT_STATUS_has_no_alertStatus_and_raw_is_ERROR() {
    verify_event_created_if_no_base_ALERT_STATUS_measure(ERROR, "Red");
  }

  @Test
  public void event_created_if_base_ALERT_STATUS_has_no_alertStatus_and_raw_is_WARN() {
    verify_event_created_if_no_base_ALERT_STATUS_measure(WARN, "Orange");
  }

  @Test
  public void event_created_if_base_ALERT_STATUS_has_invalid_alertStatus_and_raw_is_ERROR() {
    verify_event_created_if_no_base_ALERT_STATUS_measure(ERROR, "Red");
  }

  @Test
  public void event_created_if_base_ALERT_STATUS_has_invalid_alertStatus_and_raw_is_WARN() {
    verify_event_created_if_no_base_ALERT_STATUS_measure(WARN, "Orange");
  }

  private void verify_event_created_if_no_base_ALERT_STATUS_measure(Measure.Level rawAlterStatus, String expectedLabel) {
    Measure.QualityGateStatus someQGStatus = new Measure.QualityGateStatus(rawAlterStatus, ALERT_TEXT);

    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue().setQualityGateStatus(someQGStatus)));
    when(measureRepository.getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue()));

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verify(measureRepository).getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verify(eventRepository).add(eq(PROJECT_COMPONENT), eventArgumentCaptor.capture());
    verifyNoMoreInteractions(measureRepository, eventRepository);

    Event event = eventArgumentCaptor.getValue();
    assertThat(event.getCategory()).isEqualTo(Event.Category.ALERT);
    assertThat(event.getName()).isEqualTo(expectedLabel);
    assertThat(event.getDescription()).isEqualTo(ALERT_TEXT);
    assertThat(event.getData()).isNull();

    verify(notificationManager).scheduleForSending(notificationArgumentCaptor.capture());
    Notification notification = notificationArgumentCaptor.getValue();
    assertThat(notification.getType()).isEqualTo("alerts");
    assertThat(notification.getFieldValue("projectKey")).isEqualTo(PROJECT_COMPONENT.getKey());
    assertThat(notification.getFieldValue("projectUuid")).isEqualTo(PROJECT_COMPONENT.getUuid());
    assertThat(notification.getFieldValue("projectName")).isEqualTo(PROJECT_COMPONENT.getName());
    assertThat(notification.getFieldValue("alertLevel")).isEqualTo(rawAlterStatus.name());
    assertThat(notification.getFieldValue("alertName")).isEqualTo(expectedLabel);
  }

  @Test
  public void no_event_created_if_base_ALERT_STATUS_measure_but_status_is_the_same() {
    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue().setQualityGateStatus(OK_QUALITY_GATE_STATUS)));
    when(measureRepository.getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue().setQualityGateStatus(OK_QUALITY_GATE_STATUS)));

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verify(measureRepository).getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verifyNoMoreInteractions(measureRepository, eventRepository);
  }

  @Test
  public void event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed() {
    verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(OK, WARN_QUALITY_GATE_STATUS, "Orange (was Green)");
    verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(OK, ERROR_QUALITY_GATE_STATUS, "Red (was Green)");
    verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(WARN, OK_QUALITY_GATE_STATUS, "Green (was Orange)");
    verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(WARN, ERROR_QUALITY_GATE_STATUS, "Red (was Orange)");
    verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(ERROR, OK_QUALITY_GATE_STATUS, "Green (was Red)");
    verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(ERROR, WARN_QUALITY_GATE_STATUS, "Orange (was Red)");
  }

  private void verify_event_created_if_base_ALERT_STATUS_measure_exists_and_status_has_changed(Measure.Level previousAlertStatus,
    Measure.QualityGateStatus newQualityGateStatus, String expectedLabel) {
    when(measureRepository.getRawMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(of(MeasureImpl.createNoValue().setQualityGateStatus(newQualityGateStatus)));
    when(measureRepository.getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric)).thenReturn(
      of(MeasureImpl.createNoValue().setQualityGateStatus(new Measure.QualityGateStatus(previousAlertStatus))));

    underTest.execute();

    verify(measureRepository).getRawMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verify(measureRepository).getBaseMeasure(PROJECT_COMPONENT, alertStatusMetric);
    verify(eventRepository).add(eq(PROJECT_COMPONENT), eventArgumentCaptor.capture());
    verifyNoMoreInteractions(measureRepository, eventRepository);

    Event event = eventArgumentCaptor.getValue();
    assertThat(event.getCategory()).isEqualTo(Event.Category.ALERT);
    assertThat(event.getName()).isEqualTo(expectedLabel);
    assertThat(event.getDescription()).isEqualTo(ALERT_TEXT);
    assertThat(event.getData()).isNull();

    verify(notificationManager).scheduleForSending(notificationArgumentCaptor.capture());
    Notification notification = notificationArgumentCaptor.getValue();
    assertThat(notification.getType()).isEqualTo("alerts");
    assertThat(notification.getFieldValue("projectKey")).isEqualTo(PROJECT_COMPONENT.getKey());
    assertThat(notification.getFieldValue("projectUuid")).isEqualTo(PROJECT_COMPONENT.getUuid());
    assertThat(notification.getFieldValue("projectName")).isEqualTo(PROJECT_COMPONENT.getName());
    assertThat(notification.getFieldValue("alertLevel")).isEqualTo(newQualityGateStatus.getStatus().name());
    assertThat(notification.getFieldValue("alertName")).isEqualTo(expectedLabel);

    reset(measureRepository, eventRepository, notificationManager);
  }

}
