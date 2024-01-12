Refactoring Types: ['Extract Method']
n/templates/FixedValueVectors.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import java.lang.Override;

<@pp.dropOutputFile />
<#list vv.types as type>
<#list type.minor as minor>
<#assign friendlyType = (minor.friendlyType!minor.boxedType!type.boxedType) />

<#if type.major == "Fixed">
<@pp.changeOutputFile name="/org/apache/drill/exec/vector/${minor.class}Vector.java" />
<#include "/@includes/license.ftl" />

package org.apache.drill.exec.vector;

<#include "/@includes/vv_imports.ftl" />

/**
 * ${minor.class} implements a vector of fixed width values.  Elements in the vector are accessed
 * by position, starting from the logical start of the vector.  Values should be pushed onto the
 * vector sequentially, but may be randomly accessed.
 *   The width of each element is ${type.width} byte(s)
 *   The equivalent Java primitive is '${minor.javaType!type.javaType}'
 *
 * Source code generated using FreeMarker template ${.template_name}
 */
@SuppressWarnings("unused")
public final class ${minor.class}Vector extends BaseDataValueVector implements FixedWidthVector{
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(${minor.class}Vector.class);

  private final FieldReader reader = new ${minor.class}ReaderImpl(${minor.class}Vector.this);
  private final Accessor accessor = new Accessor();
  private final Mutator mutator = new Mutator();

  private int allocationValueCount = INITIAL_VALUE_ALLOCATION;
  private int allocationMonitor = 0;

  public ${minor.class}Vector(MaterializedField field, BufferAllocator allocator) {
    super(field, allocator);
  }

  @Override
  public FieldReader getReader(){
    return reader;
  }

  public int getValueCapacity(){
    return (int) (data.capacity() *1.0 / ${type.width});
  }

  public Accessor getAccessor(){
    return accessor;
  }

  public Mutator getMutator(){
    return mutator;
  }

  @Override
  public void setInitialCapacity(int numRecords) {
    allocationValueCount = numRecords;
  }

  public void allocateNew() {
    if(!allocateNewSafe()){
      throw new OutOfMemoryRuntimeException("Failure while allocating buffer.");
    }
  }

  public boolean allocateNewSafe() {
    clear();
    if (allocationMonitor > 10) {
      allocationValueCount = Math.max(8, (int) (allocationValueCount / 2));
      allocationMonitor = 0;
    } else if (allocationMonitor < -2) {
      allocationValueCount = (int) (allocationValueCount * 2);
      allocationMonitor = 0;
    }

    DrillBuf newBuf = allocator.buffer(allocationValueCount * ${type.width});
    if(newBuf == null) {
      return false;
    }

    this.data = newBuf;
    this.data.readerIndex(0);
    return true;
  }

  /**
   * Allocate a new buffer that supports setting at least the provided number of values.  May actually be sized bigger depending on underlying buffer rounding size. Must be called prior to using the ValueVector.
   * @param valueCount
   * @throws org.apache.drill.exec.memory.OutOfMemoryRuntimeException if it can't allocate the new buffer
   */
  public void allocateNew(int valueCount) {
    clear();

    DrillBuf newBuf = allocator.buffer(valueCount * ${type.width});
    if (newBuf == null) {
      throw new OutOfMemoryRuntimeException(
        String.format("Failure while allocating buffer of %d bytes",valueCount * ${type.width}));
    }

    this.data = newBuf;
    this.data.readerIndex(0);
    this.allocationValueCount = valueCount;
  }

/**
 * Allocate new buffer with double capacity, and copy data into the new buffer. Replace vector's buffer with new buffer, and release old one
 *
 * @throws org.apache.drill.exec.memory.OutOfMemoryRuntimeException if it can't allocate the new buffer
 */
  public void reAlloc() {
    logger.info("Realloc vector {}. [{}] -> [{}]", field, allocationValueCount * ${type.width}, allocationValueCount * 2 * ${type.width});
    allocationValueCount *= 2;
    DrillBuf newBuf = allocator.buffer(allocationValueCount * ${type.width});
    if (newBuf == null) {
      throw new OutOfMemoryRuntimeException(
      String.format("Failure while reallocating buffer to %d bytes",allocationValueCount * ${type.width}));
    }

    newBuf.setBytes(0, data, 0, data.capacity());
    newBuf.setZero(newBuf.capacity() / 2, newBuf.capacity() / 2);
    newBuf.writerIndex(data.writerIndex());
    data.release();
    data = newBuf;
  }

  public void zeroVector() {
    data.setZero(0, data.capacity());
  }

  @Override
  public int load(int valueCount, DrillBuf buf){
    clear();
    int len = valueCount * ${type.width};
    data = buf.slice(0, len);
    data.retain();
    data.writerIndex(len);
    return len;
  }

  @Override
  public void load(SerializedField metadata, DrillBuf buffer) {
    assert this.field.matches(metadata) : String.format("The field %s doesn't match the provided metadata %s.", this.field, metadata);
    int loaded = load(metadata.getValueCount(), buffer);
    assert metadata.getBufferLength() == loaded : String.format("Expected to load %d bytes but actually loaded %d bytes", metadata.getBufferLength(), loaded);
  }

  public TransferPair getTransferPair(){
    return new TransferImpl(getField());
  }
  public TransferPair getTransferPair(FieldReference ref){
    return new TransferImpl(getField().withPath(ref));
  }

  public TransferPair makeTransferPair(ValueVector to) {
    return new TransferImpl((${minor.class}Vector) to);
  }

  public void transferTo(${minor.class}Vector target){
    target.clear();
    target.data = data;
    target.data.retain();
    target.data.writerIndex(data.writerIndex());
    clear();
  }

  public void splitAndTransferTo(int startIndex, int length, ${minor.class}Vector target) {
    int currentWriterIndex = data.writerIndex();
    int startPoint = startIndex * ${type.width};
    int sliceLength = length * ${type.width};
    target.clear();
    target.data = this.data.slice(startPoint, sliceLength);
    target.data.writerIndex(sliceLength);
    target.data.retain();
  }

  private class TransferImpl implements TransferPair{
    ${minor.class}Vector to;

    public TransferImpl(MaterializedField field){
      this.to = new ${minor.class}Vector(field, allocator);
    }

    public TransferImpl(${minor.class}Vector to) {
      this.to = to;
    }

    public ${minor.class}Vector getTo(){
      return to;
    }

    public void transfer(){
      transferTo(to);
    }

    public void splitAndTransfer(int startIndex, int length) {
      splitAndTransferTo(startIndex, length, to);
    }

    @Override
    public void copyValueSafe(int fromIndex, int toIndex) {
      to.copyFromSafe(fromIndex, toIndex, ${minor.class}Vector.this);
    }
  }

  public void copyFrom(int fromIndex, int thisIndex, ${minor.class}Vector from){
    <#if (type.width > 8)>
    from.data.getBytes(fromIndex * ${type.width}, data, thisIndex * ${type.width}, ${type.width});
    <#else> <#-- type.width <= 8 -->
    data.set${(minor.javaType!type.javaType)?cap_first}(thisIndex * ${type.width},
        from.data.get${(minor.javaType!type.javaType)?cap_first}(fromIndex * ${type.width})
    );
    </#if> <#-- type.width -->
  }

  public void copyFromSafe(int fromIndex, int thisIndex, ${minor.class}Vector from){
    while(thisIndex >= getValueCapacity()) {
        reAlloc();
    }
    copyFrom(fromIndex, thisIndex, from);
  }

  public void decrementAllocationMonitor() {
    if (allocationMonitor > 0) {
      allocationMonitor = 0;
    }
    --allocationMonitor;
  }

  private void incrementAllocationMonitor() {
    ++allocationMonitor;
  }

  public final class Accessor extends BaseDataValueVector.BaseAccessor {

    public int getValueCount() {
      return data.writerIndex() / ${type.width};
    }

    public boolean isNull(int index){
      return false;
    }

    <#if (type.width > 8)>

    public ${minor.javaType!type.javaType} get(int index) {
      return data.slice(index * ${type.width}, ${type.width});
    }

    <#if (minor.class == "Interval")>
    public void get(int index, ${minor.class}Holder holder){

      int offsetIndex = index * ${type.width};
      holder.months = data.getInt(offsetIndex);
      holder.days = data.getInt(offsetIndex + ${minor.daysOffset});
      holder.milliseconds = data.getInt(offsetIndex + ${minor.millisecondsOffset});
    }

    public void get(int index, Nullable${minor.class}Holder holder){
      int offsetIndex = index * ${type.width};
      holder.isSet = 1;
      holder.months = data.getInt(offsetIndex);
      holder.days = data.getInt(offsetIndex + ${minor.daysOffset});
      holder.milliseconds = data.getInt(offsetIndex + ${minor.millisecondsOffset});
    }

    @Override
    public ${friendlyType} getObject(int index) {
      int offsetIndex = index * ${type.width};
      int months  = data.getInt(offsetIndex);
      int days    = data.getInt(offsetIndex + ${minor.daysOffset});
      int millis = data.getInt(offsetIndex + ${minor.millisecondsOffset});
      Period p = new Period();
      return p.plusMonths(months).plusDays(days).plusMillis(millis);
    }

    public StringBuilder getAsStringBuilder(int index) {

      int offsetIndex = index * ${type.width};

      int months  = data.getInt(offsetIndex);
      int days    = data.getInt(offsetIndex + ${minor.daysOffset});
      int millis = data.getInt(offsetIndex + ${minor.millisecondsOffset});

      int years  = (months / org.apache.drill.exec.expr.fn.impl.DateUtility.yearsToMonths);
      months = (months % org.apache.drill.exec.expr.fn.impl.DateUtility.yearsToMonths);

      int hours  = millis / (org.apache.drill.exec.expr.fn.impl.DateUtility.hoursToMillis);
      millis     = millis % (org.apache.drill.exec.expr.fn.impl.DateUtility.hoursToMillis);

      int minutes = millis / (org.apache.drill.exec.expr.fn.impl.DateUtility.minutesToMillis);
      millis      = millis % (org.apache.drill.exec.expr.fn.impl.DateUtility.minutesToMillis);

      long seconds = millis / (org.apache.drill.exec.expr.fn.impl.DateUtility.secondsToMillis);
      millis      = millis % (org.apache.drill.exec.expr.fn.impl.DateUtility.secondsToMillis);

      String yearString = (Math.abs(years) == 1) ? " year " : " years ";
      String monthString = (Math.abs(months) == 1) ? " month " : " months ";
      String dayString = (Math.abs(days) == 1) ? " day " : " days ";


      return(new StringBuilder().
             append(years).append(yearString).
             append(months).append(monthString).
             append(days).append(dayString).
             append(hours).append(":").
             append(minutes).append(":").
             append(seconds).append(".").
             append(millis));
    }

    <#elseif (minor.class == "IntervalDay")>
    public void get(int index, ${minor.class}Holder holder){

      int offsetIndex = index * ${type.width};
      holder.days = data.getInt(offsetIndex);
      holder.milliseconds = data.getInt(offsetIndex + ${minor.millisecondsOffset});
    }

    public void get(int index, Nullable${minor.class}Holder holder){
      int offsetIndex = index * ${type.width};
      holder.isSet = 1;
      holder.days = data.getInt(offsetIndex);
      holder.milliseconds = data.getInt(offsetIndex + ${minor.millisecondsOffset});
    }

    @Override
    public ${friendlyType} getObject(int index) {
      int offsetIndex = index * ${type.width};
      int millis = data.getInt(offsetIndex + ${minor.millisecondsOffset});
      int  days   = data.getInt(offsetIndex);
      Period p = new Period();
      return p.plusDays(days).plusMillis(millis);
    }


    public StringBuilder getAsStringBuilder(int index) {
      int offsetIndex = index * ${type.width};

      int millis = data.getInt(offsetIndex + ${minor.millisecondsOffset});
      int  days   = data.getInt(offsetIndex);

      int hours  = millis / (org.apache.drill.exec.expr.fn.impl.DateUtility.hoursToMillis);
      millis     = millis % (org.apache.drill.exec.expr.fn.impl.DateUtility.hoursToMillis);

      int minutes = millis / (org.apache.drill.exec.expr.fn.impl.DateUtility.minutesToMillis);
      millis      = millis % (org.apache.drill.exec.expr.fn.impl.DateUtility.minutesToMillis);

      int seconds = millis / (org.apache.drill.exec.expr.fn.impl.DateUtility.secondsToMillis);
      millis      = millis % (org.apache.drill.exec.expr.fn.impl.DateUtility.secondsToMillis);

      String dayString = (Math.abs(days) == 1) ? " day " : " days ";

      return(new StringBuilder().
              append(days).append(dayString).
              append(hours).append(":").
              append(minutes).append(":").
              append(seconds).append(".").
              append(millis));
    }

    <#elseif (minor.class == "Decimal28Sparse") || (minor.class == "Decimal38Sparse") || (minor.class == "Decimal28Dense") || (minor.class == "Decimal38Dense")>

    public void get(int index, ${minor.class}Holder holder) {
        holder.start = index * ${type.width};
        holder.buffer = data;
        holder.scale = getField().getScale();
        holder.precision = getField().getPrecision();
    }

    public void get(int index, Nullable${minor.class}Holder holder) {
        holder.isSet = 1;
        holder.start = index * ${type.width};
        holder.buffer = data;
        holder.scale = getField().getScale();
        holder.precision = getField().getPrecision();
    }

      @Override
      public ${friendlyType} getObject(int index) {
      <#if (minor.class == "Decimal28Sparse") || (minor.class == "Decimal38Sparse")>
      // Get the BigDecimal object
      return org.apache.drill.exec.util.DecimalUtility.getBigDecimalFromSparse(data, index * ${type.width}, ${minor.nDecimalDigits}, getField().getScale());
      <#else>
      return org.apache.drill.exec.util.DecimalUtility.getBigDecimalFromDense(data, index * ${type.width}, ${minor.nDecimalDigits}, getField().getScale(), ${minor.maxPrecisionDigits}, ${type.width});
      </#if>
    }

    <#else>
    public void get(int index, ${minor.class}Holder holder){
      holder.buffer = data;
      holder.start = index * ${type.width};
    }

    public void get(int index, Nullable${minor.class}Holder holder){
      holder.isSet = 1;
      holder.buffer = data;
      holder.start = index * ${type.width};
    }

    @Override
    public ${friendlyType} getObject(int index) {
      return data.slice(index * ${type.width}, ${type.width})
    }

    </#if>
    <#else> <#-- type.width <= 8 -->

    public ${minor.javaType!type.javaType} get(int index) {
      return data.get${(minor.javaType!type.javaType)?cap_first}(index * ${type.width});
    }

    <#if type.width == 4>
    public long getTwoAsLong(int index) {
      return data.getLong(index * ${type.width});
    }

    </#if>

    <#if minor.class == "Date">
    public ${friendlyType} getObject(int index) {
        org.joda.time.DateTime date = new org.joda.time.DateTime(get(index), org.joda.time.DateTimeZone.UTC);
        date = date.withZoneRetainFields(org.joda.time.DateTimeZone.getDefault());
        return date;
    }

    <#elseif minor.class == "TimeStamp">
    public ${friendlyType} getObject(int index) {
        org.joda.time.DateTime date = new org.joda.time.DateTime(get(index), org.joda.time.DateTimeZone.UTC);
        date = date.withZoneRetainFields(org.joda.time.DateTimeZone.getDefault());
        return date;
    }

    <#elseif minor.class == "IntervalYear">
    public ${friendlyType} getObject(int index) {

      int value = get(index);

      int years  = (value / org.apache.drill.exec.expr.fn.impl.DateUtility.yearsToMonths);
      int months = (value % org.apache.drill.exec.expr.fn.impl.DateUtility.yearsToMonths);
      Period p = new Period();
      return p.plusYears(years).plusMonths(months);
    }

    public StringBuilder getAsStringBuilder(int index) {

      int months  = data.getInt(index);

      int years  = (months / org.apache.drill.exec.expr.fn.impl.DateUtility.yearsToMonths);
      months = (months % org.apache.drill.exec.expr.fn.impl.DateUtility.yearsToMonths);

      String yearString = (Math.abs(years) == 1) ? " year " : " years ";
      String monthString = (Math.abs(months) == 1) ? " month " : " months ";

      return(new StringBuilder().
             append(years).append(yearString).
             append(months).append(monthString));
    }

    <#elseif minor.class == "Time">
    @Override
    public DateTime getObject(int index) {

        org.joda.time.DateTime time = new org.joda.time.DateTime(get(index), org.joda.time.DateTimeZone.UTC);
        time = time.withZoneRetainFields(org.joda.time.DateTimeZone.getDefault());
        return time;
    }



    <#elseif minor.class == "Decimal9" || minor.class == "Decimal18">
    @Override
    public ${friendlyType} getObject(int index) {

        BigInteger value = BigInteger.valueOf(((${type.boxedType})get(index)).${type.javaType}Value());
        return new BigDecimal(value, getField().getScale());
    }

    <#else>
    public ${friendlyType} getObject(int index) {
      return get(index);
    }
    public ${minor.javaType!type.javaType} getPrimitiveObject(int index) {
      return get(index);
    }
    </#if>

    public void get(int index, ${minor.class}Holder holder){
      <#if minor.class.startsWith("Decimal")>
      holder.scale = getField().getScale();
      holder.precision = getField().getPrecision();
      </#if>

      holder.value = data.get${(minor.javaType!type.javaType)?cap_first}(index * ${type.width});
    }

    public void get(int index, Nullable${minor.class}Holder holder){
      holder.isSet = 1;
      holder.value = data.get${(minor.javaType!type.javaType)?cap_first}(index * ${type.width});
    }


   </#if> <#-- type.width -->
 }

 /**
  * ${minor.class}.Mutator implements a mutable vector of fixed width values.  Elements in the
  * vector are accessed by position from the logical start of the vector.  Values should be pushed
  * onto the vector sequentially, but may be randomly accessed.
  *   The width of each element is ${type.width} byte(s)
  *   The equivalent Java primitive is '${minor.javaType!type.javaType}'
  *
  * NB: this class is automatically generated from ValueVectorTypes.tdd using FreeMarker.
  */
  public final class Mutator extends BaseDataValueVector.BaseMutator {

    private Mutator(){};
   /**
    * Set the element at the given index to the given value.  Note that widths smaller than
    * 32 bits are handled by the DrillBuf interface.
    *
    * @param index   position of the bit to set
    * @param value   value to set
    */
  <#if (type.width > 8)>
   public void set(int index, <#if (type.width > 4)>${minor.javaType!type.javaType}<#else>int</#if> value) {
     data.setBytes(index * ${type.width}, value, 0, ${type.width});
   }

   public void setSafe(int index, <#if (type.width > 4)>${minor.javaType!type.javaType}<#else>int</#if> value) {
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     data.setBytes(index * ${type.width}, value, 0, ${type.width});
   }

  <#if (minor.class == "Interval")>
   public void set(int index, int months, int days, int milliseconds){
     int offsetIndex = index * ${type.width};
     data.setInt(offsetIndex, months);
     data.setInt((offsetIndex + ${minor.daysOffset}), days);
     data.setInt((offsetIndex + ${minor.millisecondsOffset}), milliseconds);
   }

   protected void set(int index, ${minor.class}Holder holder){
     set(index, holder.months, holder.days, holder.milliseconds);
   }

   protected void set(int index, Nullable${minor.class}Holder holder){
     set(index, holder.months, holder.days, holder.milliseconds);
   }

   public void setSafe(int index, int months, int days, int milliseconds){
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, months, days, milliseconds);
   }

   public void setSafe(int index, Nullable${minor.class}Holder holder){
     setSafe(index, holder.months, holder.days, holder.milliseconds);
   }

   public void setSafe(int index, ${minor.class}Holder holder){
     setSafe(index, holder.months, holder.days, holder.milliseconds);
   }

   <#elseif (minor.class == "IntervalDay")>
   public void set(int index, int days, int milliseconds){
     int offsetIndex = index * ${type.width};
     data.setInt(offsetIndex, days);
     data.setInt((offsetIndex + ${minor.millisecondsOffset}), milliseconds);
   }

   protected void set(int index, ${minor.class}Holder holder){
     set(index, holder.days, holder.milliseconds);
   }
   protected void set(int index, Nullable${minor.class}Holder holder){
     set(index, holder.days, holder.milliseconds);
   }

   public void setSafe(int index, int days, int milliseconds){
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, days, milliseconds);
   }

   public void setSafe(int index, ${minor.class}Holder holder){
     setSafe(index, holder.days, holder.milliseconds);
   }

   public void setSafe(int index, Nullable${minor.class}Holder holder){
     setSafe(index, holder.days, holder.milliseconds);
   }

   <#elseif (minor.class == "Decimal28Sparse" || minor.class == "Decimal38Sparse") || (minor.class == "Decimal28Dense") || (minor.class == "Decimal38Dense")>

   public void set(int index, ${minor.class}Holder holder){
     set(index, holder.start, holder.buffer);
   }

   void set(int index, Nullable${minor.class}Holder holder){
     set(index, holder.start, holder.buffer);
   }

   public void setSafe(int index,  Nullable${minor.class}Holder holder){
     setSafe(index, holder.start, holder.buffer);
   }
   public void setSafe(int index,  ${minor.class}Holder holder){
     setSafe(index, holder.start, holder.buffer);
   }

   public void setSafe(int index, int start, DrillBuf buffer){
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, start, buffer);
   }

   public void set(int index, int start, DrillBuf buffer){
     data.setBytes(index * ${type.width}, buffer, start, ${type.width});
   }

   <#else>

   protected void set(int index, ${minor.class}Holder holder){
     set(index, holder.start, holder.buffer);
   }

   public void set(int index, Nullable${minor.class}Holder holder){
     set(index, holder.start, holder.buffer);
   }

   public void set(int index, int start, DrillBuf buffer){
     data.setBytes(index * ${type.width}, buffer, start, ${type.width});
   }

   public void setSafe(int index, ${minor.class}Holder holder){
     setSafe(index, holder.start, holder.buffer);
   }
   public void setSafe(int index, Nullable${minor.class}Holder holder){
     setSafe(index, holder.start, holder.buffer);
   }

   public void setSafe(int index, int start, DrillBuf buffer){
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, holder);
   }

   public void set(int index, Nullable${minor.class}Holder holder){
     data.setBytes(index * ${type.width}, holder.buffer, holder.start, ${type.width});
   }
   </#if>

   @Override
   public void generateTestData(int count) {
     setValueCount(count);
     boolean even = true;
     for(int i =0; i < getAccessor().getValueCount(); i++, even = !even){
       byte b = even ? Byte.MIN_VALUE : Byte.MAX_VALUE;
       for(int w = 0; w < ${type.width}; w++){
         data.setByte(i + w, b);
       }
     }
   }




   <#else> <#-- type.width <= 8 -->
   public void set(int index, <#if (type.width >= 4)>${minor.javaType!type.javaType}<#else>int</#if> value) {
     data.set${(minor.javaType!type.javaType)?cap_first}(index * ${type.width}, value);
   }

   public void setSafe(int index, <#if (type.width >= 4)>${minor.javaType!type.javaType}<#else>int</#if> value) {
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, value);
   }

   protected void set(int index, ${minor.class}Holder holder){
     data.set${(minor.javaType!type.javaType)?cap_first}(index * ${type.width}, holder.value);
   }

   public void setSafe(int index, ${minor.class}Holder holder){
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, holder);
   }

   protected void set(int index, Nullable${minor.class}Holder holder){
     data.set${(minor.javaType!type.javaType)?cap_first}(index * ${type.width}, holder.value);
   }

   public void setSafe(int index, Nullable${minor.class}Holder holder){
     while(index >= getValueCapacity()) {
       reAlloc();
     }
     set(index, holder);
   }

   @Override
   public void generateTestData(int size) {
     setValueCount(size);
     boolean even = true;
     for(int i =0; i < getAccessor().getValueCount(); i++, even = !even){
       if(even){
         set(i, ${minor.boxedType!type.boxedType}.MIN_VALUE);
       }else{
         set(i, ${minor.boxedType!type.boxedType}.MAX_VALUE);
       }
     }
   }


   public void generateTestDataAlt(int size) {
     setValueCount(size);
     boolean even = true;
     for(int i =0; i < getAccessor().getValueCount(); i++, even = !even){
       if(even){
         set(i, (${(minor.javaType!type.javaType)}) 1);
       }else{
         set(i, (${(minor.javaType!type.javaType)}) 0);
       }
     }
   }

  </#if> <#-- type.width -->



   public void setValueCount(int valueCount) {
     int currentValueCapacity = getValueCapacity();
     int idx = (${type.width} * valueCount);
     while(valueCount > getValueCapacity()) {
       reAlloc();
     }
     if (valueCount > 0 && currentValueCapacity > valueCount * 2) {
       incrementAllocationMonitor();
     } else if (allocationMonitor > 0) {
       allocationMonitor = 0;
     }
     VectorTrimmer.trim(data, idx);
     data.writerIndex(valueCount * ${type.width});
   }





 }
}

</#if> <#-- type.major -->
</#list>
</#list>


File: exec/java-exec/src/main/codegen/templates/NullableValueVectors.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import org.apache.drill.exec.vector.BaseDataValueVector;
import org.apache.drill.exec.vector.NullableVectorDefinitionSetter;

import java.lang.Override;
import java.lang.UnsupportedOperationException;

<@pp.dropOutputFile />
<#list vv.types as type>
<#list type.minor as minor>

<#assign className = "Nullable${minor.class}Vector" />
<#assign valuesName = "${minor.class}Vector" />
<#assign friendlyType = (minor.friendlyType!minor.boxedType!type.boxedType) />

<@pp.changeOutputFile name="/org/apache/drill/exec/vector/${className}.java" />

<#include "/@includes/license.ftl" />

package org.apache.drill.exec.vector;

<#include "/@includes/vv_imports.ftl" />

/**
 * Nullable${minor.class} implements a vector of values which could be null.  Elements in the vector
 * are first checked against a fixed length vector of boolean values.  Then the element is retrieved
 * from the base class (if not null).
 *
 * NB: this class is automatically generated from ValueVectorTypes.tdd using FreeMarker.
 */
@SuppressWarnings("unused")
public final class ${className} extends BaseDataValueVector implements <#if type.major == "VarLen">VariableWidth<#else>FixedWidth</#if>Vector, NullableVector{
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(${className}.class);

  private final FieldReader reader = new Nullable${minor.class}ReaderImpl(Nullable${minor.class}Vector.this);

  private final UInt1Vector bits = new UInt1Vector(MaterializedField.create(field + "_bits", Types.required(MinorType.UINT1)), allocator);
  private final ${valuesName} values = new ${minor.class}Vector(field, allocator);
  private final Mutator mutator = new Mutator();
  private final Accessor accessor = new Accessor();

  public ${className}(MaterializedField field, BufferAllocator allocator) {
    super(field, allocator);
  }

  @Override
  public FieldReader getReader(){
    return reader;
  }

  public int getValueCapacity(){
    return Math.min(bits.getValueCapacity(), values.getValueCapacity());
  }

  @Override
  public DrillBuf[] getBuffers(boolean clear) {
    DrillBuf[] buffers = ObjectArrays.concat(bits.getBuffers(false), values.getBuffers(false), DrillBuf.class);
    if (clear) {
      for (DrillBuf buffer:buffers) {
        buffer.retain();
      }
      clear();
    }
    return buffers;
  }

  @Override
  public void clear() {
    bits.clear();
    values.clear();
    super.clear();
  }

  public int getBufferSize(){
    return values.getBufferSize() + bits.getBufferSize();
  }

  @Override
  public DrillBuf getBuffer() {
    return values.getBuffer();
  }

  public ${valuesName} getValuesVector() {
    return values;
  }

  @Override
  public void setInitialCapacity(int numRecords) {
    bits.setInitialCapacity(numRecords);
    values.setInitialCapacity(numRecords);
  }

  <#if type.major == "VarLen">
  @Override
  public SerializedField getMetadata() {
    return getMetadataBuilder()
             .setValueCount(getAccessor().getValueCount())
             .setVarByteLength(values.getVarByteLength())
             .setBufferLength(getBufferSize())
             .build();
  }

  public void allocateNew() {
    if(!allocateNewSafe()){
      throw new OutOfMemoryRuntimeException("Failure while allocating buffer.");
    }
  }

  @Override
  public boolean allocateNewSafe() {
    /* Boolean to keep track if all the memory allocations were successful
     * Used in the case of composite vectors when we need to allocate multiple
     * buffers for multiple vectors. If one of the allocations failed we need to
     * clear all the memory that we allocated
     */
    boolean success = false;
    try {
      if(!values.allocateNewSafe()) return false;
      if(!bits.allocateNewSafe()) return false;
      success = true;
    } finally {
      if (!success) {
        clear();
      }
    }
    bits.zeroVector();
    mutator.reset();
    accessor.reset();
    return true;
  }

  @Override
  public void allocateNew(int totalBytes, int valueCount) {
    try {
      values.allocateNew(totalBytes, valueCount);
      bits.allocateNew(valueCount);
    } catch(OutOfMemoryRuntimeException e){
      clear();
      throw e;
    }
    bits.zeroVector();
    mutator.reset();
    accessor.reset();
  }

  @Override
  public int load(int dataBytes, int valueCount, DrillBuf buf){
    clear();
    int loaded = bits.load(valueCount, buf);

    // remove bits part of buffer.
    buf = buf.slice(loaded, buf.capacity() - loaded);
    dataBytes -= loaded;
    loaded += values.load(dataBytes, valueCount, buf);
    this.mutator.lastSet = valueCount;
    return loaded;
  }

  @Override
  public void load(SerializedField metadata, DrillBuf buffer) {
    assert this.field.matches(metadata) : String.format("The field %s doesn't match the provided metadata %s.", this.field, metadata);
    int loaded = load(metadata.getBufferLength(), metadata.getValueCount(), buffer);
    assert metadata.getBufferLength() == loaded : String.format("Expected to load %d bytes but actually loaded %d bytes", metadata.getBufferLength(), loaded);
  }

  @Override
  public int getByteCapacity(){
    return values.getByteCapacity();
  }

  @Override
  public int getCurrentSizeInBytes(){
    return values.getCurrentSizeInBytes();
  }

  <#else>

  @Override
  public void allocateNew() {
    try {
      values.allocateNew();
      bits.allocateNew();
    } catch(OutOfMemoryRuntimeException e) {
      clear();
      throw e;
    }
    bits.zeroVector();
    mutator.reset();
    accessor.reset();
  }


  @Override
  public boolean allocateNewSafe() {
    /* Boolean to keep track if all the memory allocations were successful
     * Used in the case of composite vectors when we need to allocate multiple
     * buffers for multiple vectors. If one of the allocations failed we need to
     * clear all the memory that we allocated
     */
    boolean success = false;
    try {
      if(!values.allocateNewSafe()) return false;
      if(!bits.allocateNewSafe()) return false;
      success = true;
    } finally {
      if (!success) {
        clear();
      }
    }
    bits.zeroVector();
    mutator.reset();
    accessor.reset();
    return true;
  }

  @Override
  public void allocateNew(int valueCount) {
    try {
      values.allocateNew(valueCount);
      bits.allocateNew(valueCount);
    } catch(OutOfMemoryRuntimeException e) {
      clear();
      throw e;
    }
    bits.zeroVector();
    mutator.reset();
    accessor.reset();
  }

  /**
   * {@inheritDoc}
   */
  public void zeroVector() {
    this.values.zeroVector();
    this.bits.zeroVector();
  }

  @Override
  public int load(int valueCount, DrillBuf buf){
    clear();
    int loaded = bits.load(valueCount, buf);

    // remove bits part of buffer.
    buf = buf.slice(loaded, buf.capacity() - loaded);
    loaded += values.load(valueCount, buf);
    return loaded;
  }

  @Override
  public void load(SerializedField metadata, DrillBuf buffer) {
    assert this.field.matches(metadata);
    int loaded = load(metadata.getValueCount(), buffer);
    assert metadata.getBufferLength() == loaded;
  }

  </#if>

  public TransferPair getTransferPair(){
    return new TransferImpl(getField());
  }
  public TransferPair getTransferPair(FieldReference ref){
    return new TransferImpl(getField().withPath(ref));
  }

  public TransferPair makeTransferPair(ValueVector to) {
    return new TransferImpl((Nullable${minor.class}Vector) to);
  }


  public void transferTo(Nullable${minor.class}Vector target){
    bits.transferTo(target.bits);
    values.transferTo(target.values);
    <#if type.major == "VarLen">
    target.mutator.lastSet = mutator.lastSet;
    </#if>
    clear();
  }

  public void splitAndTransferTo(int startIndex, int length, Nullable${minor.class}Vector target) {
    bits.splitAndTransferTo(startIndex, length, target.bits);
    values.splitAndTransferTo(startIndex, length, target.values);
    <#if type.major == "VarLen">
    target.mutator.lastSet = length - 1;
    </#if>
  }

  private class TransferImpl implements TransferPair{
    Nullable${minor.class}Vector to;

    public TransferImpl(MaterializedField field){
      this.to = new Nullable${minor.class}Vector(field, allocator);
    }

    public TransferImpl(Nullable${minor.class}Vector to){
      this.to = to;
    }

    public Nullable${minor.class}Vector getTo(){
      return to;
    }

    public void transfer(){
      transferTo(to);
    }

    public void splitAndTransfer(int startIndex, int length) {
      splitAndTransferTo(startIndex, length, to);
    }

    @Override
    public void copyValueSafe(int fromIndex, int toIndex) {
      to.copyFromSafe(fromIndex, toIndex, Nullable${minor.class}Vector.this);
    }
  }

  public Accessor getAccessor(){
    return accessor;
  }

  public Mutator getMutator(){
    return mutator;
  }

  public ${minor.class}Vector convertToRequiredVector(){
    ${minor.class}Vector v = new ${minor.class}Vector(getField().getOtherNullableVersion(), allocator);
    v.data = values.data;
    v.data.retain();
    clear();
    return v;
  }


  public void copyFrom(int fromIndex, int thisIndex, Nullable${minor.class}Vector from){
    if (!from.getAccessor().isNull(fromIndex)) {
      mutator.set(thisIndex, from.getAccessor().get(fromIndex));
    }
  }


  public void copyFromSafe(int fromIndex, int thisIndex, ${minor.class}Vector from){
    <#if type.major == "VarLen">
    mutator.fillEmpties(thisIndex);
    </#if>
    values.copyFromSafe(fromIndex, thisIndex, from);
    bits.getMutator().setSafe(thisIndex, 1);
  }

  public void copyFromSafe(int fromIndex, int thisIndex, Nullable${minor.class}Vector from){
    <#if type.major == "VarLen">
    mutator.fillEmpties(thisIndex);
    </#if>
    bits.copyFromSafe(fromIndex, thisIndex, from.bits);
    values.copyFromSafe(fromIndex, thisIndex, from.values);
  }

  public final class Accessor extends BaseDataValueVector.BaseAccessor <#if type.major = "VarLen">implements VariableWidthVector.VariableWidthAccessor</#if> {

    final UInt1Vector.Accessor bAccessor = bits.getAccessor();
    final ${valuesName}.Accessor vAccessor = values.getAccessor();

    /**
     * Get the element at the specified position.
     *
     * @param   index   position of the value
     * @return  value of the element, if not null
     * @throws  NullValueException if the value is null
     */
    public <#if type.major == "VarLen">byte[]<#else>${minor.javaType!type.javaType}</#if> get(int index) {
      if (isNull(index)) {
          throw new IllegalStateException("Can't get a null value");
      }
      return vAccessor.get(index);
    }

    public boolean isNull(int index) {
      return isSet(index) == 0;
    }

    public int isSet(int index){
      return bAccessor.get(index);
    }

    <#if type.major == "VarLen">
    public long getStartEnd(int index){
      return vAccessor.getStartEnd(index);
    }

    public int getValueLength(int index) {
      return values.getAccessor().getValueLength(index);
    }
    </#if>

    public void get(int index, Nullable${minor.class}Holder holder){
      vAccessor.get(index, holder);
      holder.isSet = bAccessor.get(index);

      <#if minor.class.startsWith("Decimal")>
      holder.scale = getField().getScale();
      holder.precision = getField().getPrecision();
      </#if>
    }

    @Override
    public ${friendlyType} getObject(int index) {
      if (isNull(index)) {
          return null;
      }else{
        return vAccessor.getObject(index);
      }
    }

    <#if minor.class == "Interval" || minor.class == "IntervalDay" || minor.class == "IntervalYear">
    public StringBuilder getAsStringBuilder(int index) {
      if (isNull(index)) {
          return null;
      }else{
        return vAccessor.getAsStringBuilder(index);
      }
    }
    </#if>

    public int getValueCount(){
      return bits.getAccessor().getValueCount();
    }

    public void reset(){}
  }

  public final class Mutator extends BaseDataValueVector.BaseMutator implements NullableVectorDefinitionSetter<#if type.major = "VarLen">, VariableWidthVector.VariableWidthMutator</#if> {

    private int setCount;
    <#if type.major = "VarLen"> private int lastSet = -1;</#if>

    private Mutator(){
    }

    public ${valuesName} getVectorWithValues(){
      return values;
    }

    public void setIndexDefined(int index){
      bits.getMutator().set(index, 1);
    }

    /**
     * Set the variable length element at the specified index to the supplied byte array.
     *
     * @param index   position of the bit to set
     * @param bytes   array of bytes to write
     */
    public void set(int index, <#if type.major == "VarLen">byte[]<#elseif (type.width < 4)>int<#else>${minor.javaType!type.javaType}</#if> value) {
      setCount++;
      <#if type.major == "VarLen">
      for (int i = lastSet + 1; i < index; i++) {
        values.getMutator().set(i, new byte[]{});
      }
      </#if>
      bits.getMutator().set(index, 1);
      values.getMutator().set(index, value);
      <#if type.major == "VarLen">lastSet = index;</#if>
    }

    <#if type.major == "VarLen">
    private void fillEmpties(int index){
      for (int i = lastSet; i < index; i++) {
        values.getMutator().setSafe(i+1, new byte[]{});
      }
      if (index > bits.getValueCapacity()) {
        bits.reAlloc();
      }
      lastSet = index;
    }

    public void setValueLengthSafe(int index, int length) {
      values.getMutator().setValueLengthSafe(index, length);
    }
    </#if>

    public void setSafe(int index, byte[] value, int start, int length) {
      <#if type.major != "VarLen">
      throw new UnsupportedOperationException();
      <#else>
      fillEmpties(index);

      bits.getMutator().setSafe(index, 1);
      values.getMutator().setSafe(index, value, start, length);
      setCount++;
      <#if type.major == "VarLen">lastSet = index;</#if>
      </#if>
    }

    public void setSafe(int index, ByteBuffer value, int start, int length) {
      <#if type.major != "VarLen">
      throw new UnsupportedOperationException();
      <#else>
      fillEmpties(index);

      bits.getMutator().setSafe(index, 1);
      values.getMutator().setSafe(index, value, start, length);
      setCount++;
      <#if type.major == "VarLen">lastSet = index;</#if>
      </#if>
    }

    public void setNull(int index){
      bits.getMutator().setSafe(index, 0);
    }

    public void setSkipNull(int index, ${minor.class}Holder holder){
      values.getMutator().set(index, holder);
    }

    public void setSkipNull(int index, Nullable${minor.class}Holder holder){
      values.getMutator().set(index, holder);
    }


    public void set(int index, Nullable${minor.class}Holder holder){
      <#if type.major == "VarLen">
      for (int i = lastSet + 1; i < index; i++) {
        values.getMutator().set(i, new byte[]{});
      }
      </#if>
      bits.getMutator().set(index, holder.isSet);
      values.getMutator().set(index, holder);
      <#if type.major == "VarLen">lastSet = index;</#if>
    }

    public void set(int index, ${minor.class}Holder holder){
      <#if type.major == "VarLen">
      for (int i = lastSet + 1; i < index; i++) {
        values.getMutator().set(i, new byte[]{});
      }
      </#if>
      bits.getMutator().set(index, 1);
      values.getMutator().set(index, holder);
      <#if type.major == "VarLen">lastSet = index;</#if>
    }

    public boolean isSafe(int outIndex) {
      return outIndex < Nullable${minor.class}Vector.this.getValueCapacity();
    }

    <#assign fields = minor.fields!type.fields />
    public void set(int index, int isSet<#list fields as field><#if field.include!true >, ${field.type} ${field.name}Field</#if></#list> ){
      <#if type.major == "VarLen">
      for (int i = lastSet + 1; i < index; i++) {
        values.getMutator().set(i, new byte[]{});
      }
      </#if>
      bits.getMutator().set(index, isSet);
      values.getMutator().set(index<#list fields as field><#if field.include!true >, ${field.name}Field</#if></#list>);
      <#if type.major == "VarLen">lastSet = index;</#if>
    }

    public void setSafe(int index, int isSet<#list fields as field><#if field.include!true >, ${field.type} ${field.name}Field</#if></#list> ) {
      <#if type.major == "VarLen">
      fillEmpties(index);
      </#if>

      bits.getMutator().setSafe(index, isSet);
      values.getMutator().setSafe(index<#list fields as field><#if field.include!true >, ${field.name}Field</#if></#list>);
      setCount++;
      <#if type.major == "VarLen">lastSet = index;</#if>
    }


    public void setSafe(int index, Nullable${minor.class}Holder value) {

      <#if type.major == "VarLen">
      fillEmpties(index);
      </#if>
      bits.getMutator().setSafe(index, value.isSet);
      values.getMutator().setSafe(index, value);
      setCount++;
      <#if type.major == "VarLen">lastSet = index;</#if>
    }

    public void setSafe(int index, ${minor.class}Holder value) {

      <#if type.major == "VarLen">
      fillEmpties(index);
      </#if>
      bits.getMutator().setSafe(index, 1);
      values.getMutator().setSafe(index, value);
      setCount++;
      <#if type.major == "VarLen">lastSet = index;</#if>
    }

    <#if !(type.major == "VarLen" || minor.class == "Decimal28Sparse" || minor.class == "Decimal38Sparse" || minor.class == "Decimal28Dense" || minor.class == "Decimal38Dense" || minor.class == "Interval" || minor.class == "IntervalDay")>
      public void setSafe(int index, ${minor.javaType!type.javaType} value) {
        <#if type.major == "VarLen">
        fillEmpties(index);
        </#if>
        bits.getMutator().setSafe(index, 1);
        values.getMutator().setSafe(index, value);
        setCount++;
      }

    </#if>

    public void setValueCount(int valueCount) {
      assert valueCount >= 0;
      <#if type.major == "VarLen">
      fillEmpties(valueCount);
      </#if>
      values.getMutator().setValueCount(valueCount);
      bits.getMutator().setValueCount(valueCount);
    }

    public void generateTestData(int valueCount){
      bits.getMutator().generateTestDataAlt(valueCount);
      values.getMutator().generateTestData(valueCount);
      <#if type.major = "VarLen">lastSet = valueCount;</#if>
      setValueCount(valueCount);
    }

    public void reset(){
      setCount = 0;
      <#if type.major = "VarLen">lastSet = -1;</#if>
    }

  }
}
</#list>
</#list>


File: exec/java-exec/src/main/codegen/templates/VariableLengthVectors.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import java.lang.Override;

import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.vector.BaseDataValueVector;
import org.apache.drill.exec.vector.BaseValueVector;
import org.apache.drill.exec.vector.VariableWidthVector;

<@pp.dropOutputFile />
<#list vv.types as type>
<#list type.minor as minor>

<#assign friendlyType = (minor.friendlyType!minor.boxedType!type.boxedType) />


<#if type.major == "VarLen">
<@pp.changeOutputFile name="/org/apache/drill/exec/vector/${minor.class}Vector.java" />

<#include "/@includes/license.ftl" />

package org.apache.drill.exec.vector;

<#include "/@includes/vv_imports.ftl" />

/**
 * ${minor.class}Vector implements a vector of variable width values.  Elements in the vector
 * are accessed by position from the logical start of the vector.  A fixed width offsetVector
 * is used to convert an element's position to it's offset from the start of the (0-based)
 * DrillBuf.  Size is inferred by adjacent elements.
 *   The width of each element is ${type.width} byte(s)
 *   The equivalent Java primitive is '${minor.javaType!type.javaType}'
 *
 * Source code generated using FreeMarker template ${.template_name}
 */
@SuppressWarnings("unused")
public final class ${minor.class}Vector extends BaseDataValueVector implements VariableWidthVector{
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(${minor.class}Vector.class);

  private static final int DEFAULT_RECORD_BYTE_COUNT = 8;
  private static final int INITIAL_BYTE_COUNT = 4096 * DEFAULT_RECORD_BYTE_COUNT;
  private static final int MIN_BYTE_COUNT = 4096;

  public final static String OFFSETS_VECTOR_NAME = "offsets";
  private final static MaterializedField offsetsField =
    MaterializedField.create(OFFSETS_VECTOR_NAME, Types.required(MinorType.UINT4));
  private final UInt${type.width}Vector offsetVector;
  private final FieldReader reader = new ${minor.class}ReaderImpl(${minor.class}Vector.this);

  private final Accessor accessor;
  private final Mutator mutator;

  private final UInt${type.width}Vector.Accessor oAccessor;


  private int allocationTotalByteCount = INITIAL_BYTE_COUNT;
  private int allocationMonitor = 0;

  public ${minor.class}Vector(MaterializedField field, BufferAllocator allocator) {
    super(field, allocator);
    this.offsetVector = new UInt${type.width}Vector(offsetsField, allocator);
    this.oAccessor = offsetVector.getAccessor();
    this.accessor = new Accessor();
    this.mutator = new Mutator();
  }

  @Override
  public FieldReader getReader(){
    return reader;
  }

  public int getBufferSize(){
    if (getAccessor().getValueCount() == 0) return 0;
    return offsetVector.getBufferSize() + data.writerIndex();
  }

  int getSizeFromCount(int valueCount) {
    return valueCount * ${type.width};
  }

  public int getValueCapacity(){
    return offsetVector.getValueCapacity() - 1;
  }

  public int getByteCapacity(){
    return data.capacity();
  }

  public int getCurrentSizeInBytes() {
    return offsetVector.getAccessor().get(getAccessor().getValueCount());
  }

  /**
   * Return the number of bytes contained in the current var len byte vector.
   * @return
   */
  public int getVarByteLength(){
    final int valueCount = getAccessor().getValueCount();
    if(valueCount == 0) return 0;
    return offsetVector.getAccessor().get(valueCount);
  }

  @Override
  public SerializedField getMetadata() {
    return getMetadataBuilder() //
             .setValueCount(getAccessor().getValueCount()) //
             .setVarByteLength(getVarByteLength()) //
             .setBufferLength(getBufferSize()) //
             .build();
  }

  public int load(int dataBytes, int valueCount, DrillBuf buf){
    if(valueCount == 0){
      allocateNew(0,0);
      return 0;
    }
    clear();
    int loaded = offsetVector.load(valueCount+1, buf);
    data = buf.slice(loaded, dataBytes - loaded);
    data.retain();
    return  dataBytes;
  }

  @Override
  public void load(SerializedField metadata, DrillBuf buffer) {
    assert this.field.matches(metadata) : String.format("The field %s doesn't match the provided metadata %s.", this.field, metadata);
    int loaded = load(metadata.getBufferLength(), metadata.getValueCount(), buffer);
    assert metadata.getBufferLength() == loaded : String.format("Expected to load %d bytes but actually loaded %d bytes", metadata.getBufferLength(), loaded);
  }

  @Override
  public void clear() {
    super.clear();
    offsetVector.clear();
  }


  @Override
  public DrillBuf[] getBuffers(boolean clear) {
    DrillBuf[] buffers = ObjectArrays.concat(offsetVector.getBuffers(false), super.getBuffers(false), DrillBuf.class);
    if (clear) {
      // does not make much sense but we have to retain buffers even when clear is set. refactor this interface.
      for (DrillBuf buffer:buffers) {
        buffer.retain();
      }
      clear();
    }
    return buffers;
  }

  public long getOffsetAddr(){
    return offsetVector.getBuffer().memoryAddress();
  }

  public UInt${type.width}Vector getOffsetVector(){
    return offsetVector;
  }

  public TransferPair getTransferPair(){
    return new TransferImpl(getField());
  }
  public TransferPair getTransferPair(FieldReference ref){
    return new TransferImpl(getField().withPath(ref));
  }

  public TransferPair makeTransferPair(ValueVector to) {
    return new TransferImpl((${minor.class}Vector) to);
  }

  public void transferTo(${minor.class}Vector target){
    target.clear();
    this.offsetVector.transferTo(target.offsetVector);
    target.data = data;
    target.data.retain();
    clear();
  }

  public void splitAndTransferTo(int startIndex, int length, ${minor.class}Vector target) {
    int startPoint = this.offsetVector.getAccessor().get(startIndex);
    int sliceLength = this.offsetVector.getAccessor().get(startIndex + length) - startPoint;
    target.offsetVector.clear();
    target.offsetVector.allocateNew(length + 1);
    for (int i = 0; i < length + 1; i++) {
      target.offsetVector.getMutator().set(i, this.offsetVector.getAccessor().get(startIndex + i) - startPoint);
    }
    target.data = this.data.slice(startPoint, sliceLength);
    target.data.retain();
    target.getMutator().setValueCount(length);
}

  protected void copyFrom(int fromIndex, int thisIndex, ${minor.class}Vector from){
    int start = from.offsetVector.getAccessor().get(fromIndex);
    int end =   from.offsetVector.getAccessor().get(fromIndex+1);
    int len = end - start;

    int outputStart = offsetVector.data.get${(minor.javaType!type.javaType)?cap_first}(thisIndex * ${type.width});
    from.data.getBytes(start, data, outputStart, len);
    offsetVector.data.set${(minor.javaType!type.javaType)?cap_first}( (thisIndex+1) * ${type.width}, outputStart + len);
  }

  public boolean copyFromSafe(int fromIndex, int thisIndex, ${minor.class}Vector from){

    int start = from.offsetVector.getAccessor().get(fromIndex);
    int end =   from.offsetVector.getAccessor().get(fromIndex+1);
    int len = end - start;

    int outputStart = offsetVector.data.get${(minor.javaType!type.javaType)?cap_first}(thisIndex * ${type.width});

    while(data.capacity() < outputStart + len) {
        reAlloc();
    }

    offsetVector.getMutator().setSafe(thisIndex + 1, outputStart + len);

    from.data.getBytes(start, data, outputStart, len);

    return true;
  }


  private class TransferImpl implements TransferPair{
    ${minor.class}Vector to;

    public TransferImpl(MaterializedField field){
      this.to = new ${minor.class}Vector(field, allocator);
    }

    public TransferImpl(${minor.class}Vector to){
      this.to = to;
    }

    public ${minor.class}Vector getTo(){
      return to;
    }

    public void transfer(){
      transferTo(to);
    }

    public void splitAndTransfer(int startIndex, int length) {
      splitAndTransferTo(startIndex, length, to);
    }

    @Override
    public void copyValueSafe(int fromIndex, int toIndex) {
      to.copyFromSafe(fromIndex, toIndex, ${minor.class}Vector.this);
    }
  }

  @Override
  public void setInitialCapacity(int numRecords) {
    allocationTotalByteCount = numRecords * DEFAULT_RECORD_BYTE_COUNT;
    offsetVector.setInitialCapacity(numRecords + 1);
  }

  public void allocateNew() {
    if(!allocateNewSafe()){
      throw new OutOfMemoryRuntimeException("Failure while allocating buffer.");
    }
  }

  @Override
  public boolean allocateNewSafe() {
    clear();
    if (allocationMonitor > 10) {
      allocationTotalByteCount = Math.max(MIN_BYTE_COUNT, (int) (allocationTotalByteCount / 2));
      allocationMonitor = 0;
    } else if (allocationMonitor < -2) {
      allocationTotalByteCount = (int) (allocationTotalByteCount * 2);
      allocationMonitor = 0;
    }

    /* Boolean to keep track if all the memory allocations were successful
     * Used in the case of composite vectors when we need to allocate multiple
     * buffers for multiple vectors. If one of the allocations failed we need to
     * clear all the memory that we allocated
     */
    boolean success = false;
    try {
      DrillBuf newBuf = allocator.buffer(allocationTotalByteCount);
      if (newBuf == null) {
        return false;
      }
      this.data = newBuf;
      if (!offsetVector.allocateNewSafe()) {
        return false;
      }
      success = true;
    } finally {
      if (!success) {
        clear();
      }
    }
    data.readerIndex(0);
    offsetVector.zeroVector();
    return true;
  }

  public void allocateNew(int totalBytes, int valueCount) {
    clear();
    assert totalBytes >= 0;
    try {
      DrillBuf newBuf = allocator.buffer(totalBytes);
      if (newBuf == null) {
        throw new OutOfMemoryRuntimeException(String.format("Failure while allocating buffer of %d bytes", totalBytes));
      }
      this.data = newBuf;
      offsetVector.allocateNew(valueCount + 1);
    } catch (OutOfMemoryRuntimeException e) {
      clear();
      throw e;
    }
    data.readerIndex(0);
    allocationTotalByteCount = totalBytes;
    offsetVector.zeroVector();
  }

    public void reAlloc() {
      allocationTotalByteCount *= 2;
      DrillBuf newBuf = allocator.buffer(allocationTotalByteCount);
      if(newBuf == null){
        throw new OutOfMemoryRuntimeException(
          String.format("Failure while reallocating buffer of %d bytes", allocationTotalByteCount));
      }

      newBuf.setBytes(0, data, 0, data.capacity());
      data.release();
      data = newBuf;
    }

  public void decrementAllocationMonitor() {
    if (allocationMonitor > 0) {
      allocationMonitor = 0;
    }
    --allocationMonitor;
  }

  private void incrementAllocationMonitor() {
    ++allocationMonitor;
  }

  public Accessor getAccessor(){
    return accessor;
  }

  public Mutator getMutator() {
    return mutator;
  }

  public final class Accessor extends BaseValueVector.BaseAccessor implements VariableWidthAccessor {
    final UInt${type.width}Vector.Accessor oAccessor = offsetVector.getAccessor();

    public long getStartEnd(int index){
      return oAccessor.getTwoAsLong(index);
    }

    public byte[] get(int index) {
      assert index >= 0;
      int startIdx = oAccessor.get(index);
      int length = oAccessor.get(index + 1) - startIdx;
      assert length >= 0;
      byte[] dst = new byte[length];
      data.getBytes(startIdx, dst, 0, length);
      return dst;
    }

    public int getValueLength(int index) {
      return offsetVector.getAccessor().get(index + 1) - offsetVector.getAccessor().get(index);
    }

    public void get(int index, ${minor.class}Holder holder){
      holder.start = oAccessor.get(index);
      holder.end = oAccessor.get(index + 1);
      holder.buffer = data;
    }

    public void get(int index, Nullable${minor.class}Holder holder){
      holder.isSet = 1;
      holder.start = oAccessor.get(index);
      holder.end = oAccessor.get(index + 1);
      holder.buffer = data;
    }


    <#switch minor.class>
    <#case "VarChar">
    public ${friendlyType} getObject(int index) {
      Text text = new Text();
      text.set(get(index));
      return text;
    }
    <#break>
    <#case "Var16Char">
    public ${friendlyType} getObject(int index) {
      return new String(get(index), Charsets.UTF_16);
    }
    <#break>
    <#default>
    public ${friendlyType} getObject(int index) {
      return get(index);
    }

    </#switch>



    public int getValueCount() {
      return Math.max(offsetVector.getAccessor().getValueCount()-1, 0);
    }

    public boolean isNull(int index){
      return false;
    }

    public UInt${type.width}Vector getOffsetVector(){
      return offsetVector;
    }
  }

  /**
   * Mutable${minor.class} implements a vector of variable width values.  Elements in the vector
   * are accessed by position from the logical start of the vector.  A fixed width offsetVector
   * is used to convert an element's position to it's offset from the start of the (0-based)
   * DrillBuf.  Size is inferred by adjacent elements.
   *   The width of each element is ${type.width} byte(s)
   *   The equivalent Java primitive is '${minor.javaType!type.javaType}'
   *
   * NB: this class is automatically generated from ValueVectorTypes.tdd using FreeMarker.
   */
  public final class Mutator extends BaseValueVector.BaseMutator implements VariableWidthVector.VariableWidthMutator {

    /**
     * Set the variable length element at the specified index to the supplied byte array.
     *
     * @param index   position of the bit to set
     * @param bytes   array of bytes to write
     */
    protected void set(int index, byte[] bytes) {
      assert index >= 0;
      int currentOffset = offsetVector.getAccessor().get(index);
      offsetVector.getMutator().set(index + 1, currentOffset + bytes.length);
      data.setBytes(currentOffset, bytes, 0, bytes.length);
    }

    public void setSafe(int index, byte[] bytes) {
      assert index >= 0;

      int currentOffset = offsetVector.getAccessor().get(index);
      while (data.capacity() < currentOffset + bytes.length) {
        reAlloc();
      }
      offsetVector.getMutator().setSafe(index + 1, currentOffset + bytes.length);
      offsetVector.getMutator().set(index + 1, currentOffset + bytes.length);
      data.setBytes(currentOffset, bytes, 0, bytes.length);
    }

    /**
     * Set the variable length element at the specified index to the supplied byte array.
     *
     * @param index   position of the bit to set
     * @param bytes   array of bytes to write
     * @param start   start index of bytes to write
     * @param length  length of bytes to write
     */
    protected void set(int index, byte[] bytes, int start, int length) {
      assert index >= 0;
      int currentOffset = offsetVector.getAccessor().get(index);
      offsetVector.getMutator().set(index + 1, currentOffset + length);
      data.setBytes(currentOffset, bytes, start, length);
    }

    public void setSafe(int index, ByteBuffer bytes, int start, int length) {
      assert index >= 0;

      int currentOffset = offsetVector.getAccessor().get(index);

      while (data.capacity() < currentOffset + length) {
        reAlloc();
      }
      offsetVector.getMutator().setSafe(index + 1, currentOffset + length);
      data.setBytes(currentOffset, bytes, start, length);
    }

    public void setSafe(int index, byte[] bytes, int start, int length) {
      assert index >= 0;

      int currentOffset = offsetVector.getAccessor().get(index);

      while (data.capacity() < currentOffset + length) {
        reAlloc();
      }
      offsetVector.getMutator().setSafe(index + 1, currentOffset + length);
      data.setBytes(currentOffset, bytes, start, length);
    }

    public void setValueLengthSafe(int index, int length) {
      int offset = offsetVector.getAccessor().get(index);
      while(data.capacity() < offset + length ) {
        reAlloc();
      }
      offsetVector.getMutator().setSafe(index + 1, offsetVector.getAccessor().get(index) + length);
    }


    public void setSafe(int index, int start, int end, DrillBuf buffer){
      int len = end - start;

      int outputStart = offsetVector.data.get${(minor.javaType!type.javaType)?cap_first}(index * ${type.width});

      while(data.capacity() < outputStart + len) {
        reAlloc();
      }

      offsetVector.getMutator().setSafe( index+1,  outputStart + len);
      buffer.getBytes(start, data, outputStart, len);
    }


    public void setSafe(int index, Nullable${minor.class}Holder holder){
      assert holder.isSet == 1;

      int start = holder.start;
      int end =   holder.end;
      int len = end - start;

      int outputStart = offsetVector.data.get${(minor.javaType!type.javaType)?cap_first}(index * ${type.width});

      while(data.capacity() < outputStart + len) {
        reAlloc();
      }

      holder.buffer.getBytes(start, data, outputStart, len);
      offsetVector.getMutator().setSafe( index+1,  outputStart + len);
    }

    public void setSafe(int index, ${minor.class}Holder holder){

      int start = holder.start;
      int end =   holder.end;
      int len = end - start;

      int outputStart = offsetVector.data.get${(minor.javaType!type.javaType)?cap_first}(index * ${type.width});

      while(data.capacity() < outputStart + len) {
        reAlloc();
      }

      holder.buffer.getBytes(start, data, outputStart, len);
      offsetVector.getMutator().setSafe( index+1,  outputStart + len);
    }

    protected void set(int index, int start, int length, DrillBuf buffer){
      assert index >= 0;
      int currentOffset = offsetVector.getAccessor().get(index);
      offsetVector.getMutator().set(index + 1, currentOffset + length);
      DrillBuf bb = buffer.slice(start, length);
      data.setBytes(currentOffset, bb);
    }

    protected void set(int index, Nullable${minor.class}Holder holder){
      int length = holder.end - holder.start;
      int currentOffset = offsetVector.getAccessor().get(index);
      offsetVector.getMutator().set(index + 1, currentOffset + length);
      data.setBytes(currentOffset, holder.buffer, holder.start, length);
    }

    protected void set(int index, ${minor.class}Holder holder){
      int length = holder.end - holder.start;
      int currentOffset = offsetVector.getAccessor().get(index);
      offsetVector.getMutator().set(index + 1, currentOffset + length);
      data.setBytes(currentOffset, holder.buffer, holder.start, length);
    }

    public void setValueCount(int valueCount) {
      int currentByteCapacity = getByteCapacity();
      int idx = offsetVector.getAccessor().get(valueCount);
      data.writerIndex(idx);
      if (valueCount > 0 && currentByteCapacity > idx * 2) {
        incrementAllocationMonitor();
      } else if (allocationMonitor > 0) {
        allocationMonitor = 0;
      }
      VectorTrimmer.trim(data, idx);
      offsetVector.getMutator().setValueCount(valueCount == 0 ? 0 : valueCount+1);
    }

    @Override
    public void generateTestData(int size){
      boolean even = true;
      <#switch minor.class>
      <#case "Var16Char">
      java.nio.charset.Charset charset = Charsets.UTF_16;
      <#break>
      <#case "VarChar">
      <#default>
      java.nio.charset.Charset charset = Charsets.UTF_8;
      </#switch>
      for(int i =0; i < size; i++, even = !even){
        if(even){
          set(i, new String("aaaaa").getBytes(charset));
        }else{
          set(i, new String("bbbbbbbbbb").getBytes(charset));
        }
      }
      setValueCount(size);
    }
  }

}


</#if> <#-- type.major -->
</#list>
</#list>


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/flatten/FlattenRecordBatch.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.flatten;

import java.io.IOException;
import java.util.List;

import com.carrotsearch.hppc.IntOpenHashSet;
import org.apache.drill.common.exceptions.UserException;
import org.apache.drill.common.expression.ErrorCollector;
import org.apache.drill.common.expression.ErrorCollectorImpl;
import org.apache.drill.common.expression.FieldReference;
import org.apache.drill.common.expression.LogicalExpression;
import org.apache.drill.common.expression.PathSegment;
import org.apache.drill.common.logical.data.NamedExpression;
import org.apache.drill.exec.exception.ClassTransformationException;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.expr.ClassGenerator;
import org.apache.drill.exec.expr.ClassGenerator.HoldingContainer;
import org.apache.drill.exec.expr.CodeGenerator;
import org.apache.drill.exec.expr.DrillFuncHolderExpr;
import org.apache.drill.exec.expr.ExpressionTreeMaterializer;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.ValueVectorReadExpression;
import org.apache.drill.exec.expr.ValueVectorWriteExpression;
import org.apache.drill.exec.expr.fn.DrillComplexWriterFuncHolder;
import org.apache.drill.exec.memory.OutOfMemoryException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.physical.config.FlattenPOP;
import org.apache.drill.exec.record.AbstractSingleRecordBatch;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.TransferPair;
import org.apache.drill.exec.record.TypedFieldId;
import org.apache.drill.exec.record.VectorContainer;
import org.apache.drill.exec.record.VectorWrapper;
import org.apache.drill.exec.vector.complex.RepeatedValueVector;
import org.apache.drill.exec.vector.ValueVector;
import org.apache.drill.exec.vector.complex.RepeatedMapVector;
import org.apache.drill.exec.vector.complex.writer.BaseWriter.ComplexWriter;

import com.google.common.collect.Lists;
import com.sun.codemodel.JExpr;

// TODO - handle the case where a user tries to flatten a scalar, should just act as a project all of the columns exactly
// as they come in
public class FlattenRecordBatch extends AbstractSingleRecordBatch<FlattenPOP> {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FlattenRecordBatch.class);

  private Flattener flattener;
  private List<ValueVector> allocationVectors;
  private List<ComplexWriter> complexWriters;
  private boolean hasRemainder = false;
  private int remainderIndex = 0;
  private int recordCount;
  // the buildSchema method is always called first by a short circuit path to return schema information to the client
  // this information is not entirely accurate as Drill determines schema on the fly, so here it needs to have modified
  // behavior for that call to setup the schema for the flatten operation
  private boolean fastSchemaCalled;

  private static final String EMPTY_STRING = "";

  private class ClassifierResult {
    public boolean isStar = false;
    public List<String> outputNames;
    public String prefix = "";

    private void clear() {
      isStar = false;
      prefix = "";
      if (outputNames != null) {
        outputNames.clear();
      }

      // note:  don't clear the internal maps since they have cumulative data..
    }
  }

  public FlattenRecordBatch(FlattenPOP pop, RecordBatch incoming, FragmentContext context) throws OutOfMemoryException {
    super(pop, context, incoming);
    fastSchemaCalled = false;
  }

  @Override
  public int getRecordCount() {
    return recordCount;
  }


  @Override
  protected void killIncoming(boolean sendUpstream) {
    super.killIncoming(sendUpstream);
    hasRemainder = false;
  }


  @Override
  public IterOutcome innerNext() {
    if (hasRemainder) {
      handleRemainder();
      return IterOutcome.OK;
    }
    return super.innerNext();
  }

  @Override
  public VectorContainer getOutgoingContainer() {
    return this.container;
  }

  private void setFlattenVector() {
    try {
      final TypedFieldId typedFieldId = incoming.getValueVectorId(popConfig.getColumn());
      final MaterializedField field = incoming.getSchema().getColumn(typedFieldId.getFieldIds()[0]);
      final RepeatedValueVector vector = RepeatedValueVector.class.cast(incoming.getValueAccessorById(
          field.getValueClass(), typedFieldId.getFieldIds()).getValueVector());
      flattener.setFlattenField(vector);
    } catch (Exception ex) {
      throw UserException.unsupportedError(ex).message("Trying to flatten a non-repeated field.").build(logger);
    }
  }

  @Override
  protected IterOutcome doWork() {
    int incomingRecordCount = incoming.getRecordCount();

    if (!doAlloc()) {
      outOfMemory = true;
      return IterOutcome.OUT_OF_MEMORY;
    }

    // we call this in setupSchema, but we also need to call it here so we have a reference to the appropriate vector
    // inside of the the flattener for the current batch
    setFlattenVector();

    int childCount = incomingRecordCount == 0 ? 0 : flattener.getFlattenField().getAccessor().getInnerValueCount();
    int outputRecords = flattener.flattenRecords(0, incomingRecordCount, 0);
    // TODO - change this to be based on the repeated vector length
    if (outputRecords < childCount) {
      setValueCount(outputRecords);
      hasRemainder = true;
      remainderIndex = outputRecords;
      this.recordCount = remainderIndex;
    } else {
      setValueCount(outputRecords);
      flattener.resetGroupIndex();
      for(VectorWrapper<?> v: incoming) {
        v.clear();
      }
      this.recordCount = outputRecords;
    }
    // In case of complex writer expression, vectors would be added to batch run-time.
    // We have to re-build the schema.
    if (complexWriters != null) {
      container.buildSchema(SelectionVectorMode.NONE);
    }

    return IterOutcome.OK;
  }

  private void handleRemainder() {
    int remainingRecordCount = flattener.getFlattenField().getAccessor().getInnerValueCount() - remainderIndex;
    if (!doAlloc()) {
      outOfMemory = true;
      return;
    }

    int projRecords = flattener.flattenRecords(remainderIndex, remainingRecordCount, 0);
    if (projRecords < remainingRecordCount) {
      setValueCount(projRecords);
      this.recordCount = projRecords;
      remainderIndex += projRecords;
    } else {
      setValueCount(remainingRecordCount);
      hasRemainder = false;
      remainderIndex = 0;
      for (VectorWrapper<?> v : incoming) {
        v.clear();
      }
      flattener.resetGroupIndex();
      this.recordCount = remainingRecordCount;
    }
    // In case of complex writer expression, vectors would be added to batch run-time.
    // We have to re-build the schema.
    if (complexWriters != null) {
      container.buildSchema(SelectionVectorMode.NONE);
    }
  }

  public void addComplexWriter(ComplexWriter writer) {
    complexWriters.add(writer);
  }

  private boolean doAlloc() {
    //Allocate vv in the allocationVectors.
    for (ValueVector v : this.allocationVectors) {
      if (!v.allocateNewSafe()) {
        return false;
      }
    }

    //Allocate vv for complexWriters.
    if (complexWriters == null) {
      return true;
    }

    for (ComplexWriter writer : complexWriters) {
      writer.allocate();
    }

    return true;
  }

  private void setValueCount(int count) {
    for (ValueVector v : allocationVectors) {
      ValueVector.Mutator m = v.getMutator();
      m.setValueCount(count);
    }

    if (complexWriters == null) {
      return;
    }

    for (ComplexWriter writer : complexWriters) {
      writer.setValueCount(count);
    }
  }

  private FieldReference getRef(NamedExpression e) {
    FieldReference ref = e.getRef();
    PathSegment seg = ref.getRootSegment();

    return ref;
  }

  /**
   * The data layout is the same for the actual data within a repeated field, as it is in a scalar vector for
   * the same sql type. For example, a repeated int vector has a vector of offsets into a regular int vector to
   * represent the lists. As the data layout for the actual values in the same in the repeated vector as in the
   * scalar vector of the same type, we can avoid making individual copies for the column being flattened, and just
   * use vector copies between the inner vector of the repeated field to the resulting scalar vector from the flatten
   * operation. This is completed after we determine how many records will fit (as we will hit either a batch end, or
   * the end of one of the other vectors while we are copying the data of the other vectors alongside each new flattened
   * value coming out of the repeated field.)
   */
  private TransferPair getFlattenFieldTransferPair(FieldReference reference) {
    final TypedFieldId fieldId = incoming.getValueVectorId(popConfig.getColumn());
    final Class vectorClass = incoming.getSchema().getColumn(fieldId.getFieldIds()[0]).getValueClass();
    final ValueVector flattenField = incoming.getValueAccessorById(vectorClass, fieldId.getFieldIds()).getValueVector();

    TransferPair tp = null;
    if (flattenField instanceof RepeatedMapVector) {
      tp = ((RepeatedMapVector)flattenField).getTransferPairToSingleMap(reference);
    } else {
      final ValueVector vvIn = RepeatedValueVector.class.cast(flattenField).getDataVector();
      // vvIn may be null because of fast schema return for repeated list vectors
      if (vvIn != null) {
        tp = vvIn.getTransferPair(reference);
      }
    }
    return tp;
  }

  @Override
  protected boolean setupNewSchema() throws SchemaChangeException {
    this.allocationVectors = Lists.newArrayList();
    container.clear();
    final List<NamedExpression> exprs = getExpressionList();
    final ErrorCollector collector = new ErrorCollectorImpl();
    final List<TransferPair> transfers = Lists.newArrayList();

    final ClassGenerator<Flattener> cg = CodeGenerator.getRoot(Flattener.TEMPLATE_DEFINITION, context.getFunctionRegistry());
    final IntOpenHashSet transferFieldIds = new IntOpenHashSet();

    final NamedExpression flattenExpr = new NamedExpression(popConfig.getColumn(), new FieldReference(popConfig.getColumn()));
    final ValueVectorReadExpression vectorRead = (ValueVectorReadExpression)ExpressionTreeMaterializer.materialize(flattenExpr.getExpr(), incoming, collector, context.getFunctionRegistry(), true);
    final TransferPair tp = getFlattenFieldTransferPair(flattenExpr.getRef());

    if (tp != null) {
      transfers.add(tp);
      container.add(tp.getTo());
      transferFieldIds.add(vectorRead.getFieldId().getFieldIds()[0]);
    }

    logger.debug("Added transfer for project expression.");

    ClassifierResult result = new ClassifierResult();

    for (int i = 0; i < exprs.size(); i++) {
      final NamedExpression namedExpression = exprs.get(i);
      result.clear();

      String outputName = getRef(namedExpression).getRootSegment().getPath();
      if (result != null && result.outputNames != null && result.outputNames.size() > 0) {
        for (int j = 0; j < result.outputNames.size(); j++) {
          if (!result.outputNames.get(j).equals(EMPTY_STRING)) {
            outputName = result.outputNames.get(j);
            break;
          }
        }
      }

      final LogicalExpression expr = ExpressionTreeMaterializer.materialize(namedExpression.getExpr(), incoming, collector, context.getFunctionRegistry(), true);
      final MaterializedField outputField = MaterializedField.create(outputName, expr.getMajorType());
      if (collector.hasErrors()) {
        throw new SchemaChangeException(String.format("Failure while trying to materialize incoming schema.  Errors:\n %s.", collector.toErrorString()));
      }
      if (expr instanceof DrillFuncHolderExpr &&
          ((DrillFuncHolderExpr) expr).isComplexWriterFuncHolder())  {
        // Need to process ComplexWriter function evaluation.
        // Lazy initialization of the list of complex writers, if not done yet.
        if (complexWriters == null) {
          complexWriters = Lists.newArrayList();
        }

        // The reference name will be passed to ComplexWriter, used as the name of the output vector from the writer.
        ((DrillComplexWriterFuncHolder) ((DrillFuncHolderExpr) expr).getHolder()).setReference(namedExpression.getRef());
        cg.addExpr(expr);
      } else{
        // need to do evaluation.
        ValueVector vector = TypeHelper.getNewVector(outputField, oContext.getAllocator());
        allocationVectors.add(vector);
        TypedFieldId fid = container.add(vector);
        ValueVectorWriteExpression write = new ValueVectorWriteExpression(fid, expr, true);
        HoldingContainer hc = cg.addExpr(write);

        logger.debug("Added eval for project expression.");
      }
    }

    cg.rotateBlock();
    cg.getEvalBlock()._return(JExpr.TRUE);

    container.buildSchema(SelectionVectorMode.NONE);

    try {
      this.flattener = context.getImplementationClass(cg.getCodeGenerator());
      flattener.setup(context, incoming, this, transfers);
    } catch (ClassTransformationException | IOException e) {
      throw new SchemaChangeException("Failure while attempting to load generated class", e);
    }
    return true;
  }

  private List<NamedExpression> getExpressionList() {

    List<NamedExpression> exprs = Lists.newArrayList();
    for (MaterializedField field : incoming.getSchema()) {
      if (field.getPath().equals(popConfig.getColumn())) {
        continue;
      }
      exprs.add(new NamedExpression(field.getPath(), new FieldReference(field.getPath())));
    }
    return exprs;
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/flatten/FlattenTemplate.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.flatten;

import java.util.List;

import javax.inject.Named;

import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.record.BatchSchema.SelectionVectorMode;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.TransferPair;
import org.apache.drill.exec.record.selection.SelectionVector2;
import org.apache.drill.exec.record.selection.SelectionVector4;

import com.google.common.collect.ImmutableList;

import org.apache.drill.exec.vector.complex.RepeatedValueVector;

public abstract class FlattenTemplate implements Flattener {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(FlattenTemplate.class);

  private static final int OUTPUT_BATCH_SIZE = 4*1024;

  private ImmutableList<TransferPair> transfers;
  private SelectionVector2 vector2;
  private SelectionVector4 vector4;
  private SelectionVectorMode svMode;
  private RepeatedValueVector fieldToFlatten;
  private RepeatedValueVector.RepeatedAccessor accessor;
  private int valueIndex;

  // this allows for groups to be written between batches if we run out of space, for cases where we have finished
  // a batch on the boundary it will be set to 0
  private int childIndexWithinCurrGroup;
  // calculating the current group size requires reading the start and end out of the offset vector, this only happens
  // once and is stored here for faster reference
  private int currGroupSize;
  private int childIndex;

  public FlattenTemplate() throws SchemaChangeException {
    childIndexWithinCurrGroup = -1;
  }

  @Override
  public void setFlattenField(RepeatedValueVector flattenField) {
    this.fieldToFlatten = flattenField;
    this.accessor = RepeatedValueVector.RepeatedAccessor.class.cast(flattenField.getAccessor());
  }

  public RepeatedValueVector getFlattenField() {
    return fieldToFlatten;
  }

  @Override
  public final int flattenRecords(int startIndex, final int recordCount, int firstOutputIndex) {
    startIndex = childIndex;
    switch (svMode) {
      case FOUR_BYTE:
        throw new UnsupportedOperationException("Flatten does not support selection vector inputs.");

      case TWO_BYTE:
        throw new UnsupportedOperationException("Flatten does not support selection vector inputs.");

      case NONE:
        if (childIndexWithinCurrGroup == -1) {
          childIndexWithinCurrGroup = 0;
        }
        outer: {
          final int valueCount = accessor.getValueCount();
          for ( ; valueIndex < valueCount; valueIndex++) {
            currGroupSize = accessor.getInnerValueCountAt(valueIndex);
            for ( ; childIndexWithinCurrGroup < currGroupSize; childIndexWithinCurrGroup++) {
              if (firstOutputIndex == OUTPUT_BATCH_SIZE) {
                break outer;
              }
              doEval(valueIndex, firstOutputIndex);
              firstOutputIndex++;
              childIndex++;
            }
            childIndexWithinCurrGroup = 0;
          }
        }
//        System.out.println(String.format("startIndex %d, recordCount %d, firstOutputIndex: %d, currGroupSize: %d, childIndexWithinCurrGroup: %d, groupIndex: %d", startIndex, recordCount, firstOutputIndex, currGroupSize, childIndexWithinCurrGroup, groupIndex));
//        try{
////          Thread.sleep(1000);
//        }catch(Exception e){
//
//        }

        for (TransferPair t : transfers) {
          t.splitAndTransfer(startIndex, childIndex - startIndex);
        }
        return childIndex - startIndex;

      default:
        throw new UnsupportedOperationException();
    }
  }

  @Override
  public final void setup(FragmentContext context, RecordBatch incoming, RecordBatch outgoing, List<TransferPair> transfers)  throws SchemaChangeException{

    this.svMode = incoming.getSchema().getSelectionVectorMode();
    switch (svMode) {
      case FOUR_BYTE:
        throw new UnsupportedOperationException("Flatten does not support selection vector inputs.");
      case TWO_BYTE:
        throw new UnsupportedOperationException("Flatten does not support selection vector inputs.");
    }
    this.transfers = ImmutableList.copyOf(transfers);
    doSetup(context, incoming, outgoing);
  }



  @Override
  public void resetGroupIndex() {
    this.valueIndex = 0;
    this.currGroupSize = 0;
    this.childIndex = 0;
  }

  public abstract void doSetup(@Named("context") FragmentContext context, @Named("incoming") RecordBatch incoming, @Named("outgoing") RecordBatch outgoing);
  public abstract boolean doEval(@Named("inIndex") int inIndex, @Named("outIndex") int outIndex);

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/physical/impl/flatten/Flattener.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.physical.impl.flatten;

import java.util.List;

import org.apache.drill.exec.compile.TemplateClassDefinition;
import org.apache.drill.exec.exception.SchemaChangeException;
import org.apache.drill.exec.ops.FragmentContext;
import org.apache.drill.exec.record.RecordBatch;
import org.apache.drill.exec.record.TransferPair;
import org.apache.drill.exec.vector.complex.RepeatedValueVector;

public interface Flattener {

  public abstract void setup(FragmentContext context, RecordBatch incoming,  RecordBatch outgoing, List<TransferPair> transfers)  throws SchemaChangeException;
  public abstract int flattenRecords(int startIndex, int recordCount, int firstOutputIndex);
  public void setFlattenField(RepeatedValueVector repeatedColumn);
  public RepeatedValueVector getFlattenField();
  public void resetGroupIndex();

  public static TemplateClassDefinition<Flattener> TEMPLATE_DEFINITION = new TemplateClassDefinition<Flattener>(Flattener.class, FlattenTemplate.class);

}

File: exec/java-exec/src/main/java/org/apache/drill/exec/vector/BaseDataValueVector.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.vector;

import io.netty.buffer.DrillBuf;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.record.MaterializedField;


public abstract class BaseDataValueVector extends BaseValueVector{

  protected DrillBuf data;

  public BaseDataValueVector(MaterializedField field, BufferAllocator allocator) {
    super(field, allocator);
    this.data = allocator.getEmpty();
  }

  @Override
  public void clear() {
    data.release();
    data = allocator.getEmpty();
    super.clear();
  }

  @Override
  public DrillBuf[] getBuffers(boolean clear) {
    DrillBuf[] out;
    if (getBufferSize() == 0) {
      out = new DrillBuf[0];
    } else {
      out = new DrillBuf[]{data};
      if (clear) {
        data.readerIndex(0);
        data.retain();
      }
    }
    if (clear) {
      clear();
    }
    return out;
  }

  public int getBufferSize() {
    if (getAccessor().getValueCount() == 0) {
      return 0;
    }
    return data.writerIndex();
  }

  public DrillBuf getBuffer() {
    return data;
  }

}


File: exec/java-exec/src/main/java/org/apache/drill/exec/vector/BaseValueVector.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.vector;

import java.util.Iterator;

import com.google.common.base.Preconditions;
import com.google.common.collect.Iterators;
import org.apache.drill.common.expression.FieldReference;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.proto.UserBitShared.SerializedField;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.TransferPair;

public abstract class BaseValueVector implements ValueVector {
  private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(BaseValueVector.class);

  protected final BufferAllocator allocator;
  protected final MaterializedField field;
  public static final int INITIAL_VALUE_ALLOCATION = 4096;

  protected BaseValueVector(MaterializedField field, BufferAllocator allocator) {
    this.field = Preconditions.checkNotNull(field, "field cannot be null");
    this.allocator = Preconditions.checkNotNull(allocator, "allocator cannot be null");
  }

  @Override
  public void clear() {
    getMutator().reset();
  }

  @Override
  public void close() {
    clear();
  }

  @Override
  public MaterializedField getField() {
    return field;
  }

  public MaterializedField getField(FieldReference ref){
    return getField().withPath(ref);
  }

  @Override
  public TransferPair getTransferPair() {
    return getTransferPair(new FieldReference(getField().getPath()));
  }

  @Override
  public SerializedField getMetadata() {
    return getMetadataBuilder().build();
  }

  protected SerializedField.Builder getMetadataBuilder() {
    return getField().getAsBuilder()
        .setValueCount(getAccessor().getValueCount())
        .setBufferLength(getBufferSize());
  }

  public abstract static class BaseAccessor implements ValueVector.Accessor {
    protected BaseAccessor() { }

    @Override
    public boolean isNull(int index) {
      return false;
    }
  }

  public abstract static class BaseMutator implements ValueVector.Mutator {
    protected BaseMutator() { }

    @Override
    public void generateTestData(int values) { }

    //TODO: consider making mutator stateless(if possible) on another issue.
    public void reset() { }
  }

  @Override
  public Iterator<ValueVector> iterator() {
    return Iterators.emptyIterator();
  }

}



File: exec/java-exec/src/main/java/org/apache/drill/exec/vector/BitVector.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.vector;

import io.netty.buffer.DrillBuf;

import org.apache.drill.common.expression.FieldReference;
import org.apache.drill.exec.expr.holders.BitHolder;
import org.apache.drill.exec.expr.holders.NullableBitHolder;
import org.apache.drill.exec.memory.BufferAllocator;
import org.apache.drill.exec.memory.OutOfMemoryRuntimeException;
import org.apache.drill.exec.proto.UserBitShared.SerializedField;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.record.TransferPair;
import org.apache.drill.exec.vector.complex.impl.BitReaderImpl;
import org.apache.drill.exec.vector.complex.reader.FieldReader;

/**
 * Bit implements a vector of bit-width values. Elements in the vector are accessed by position from the logical start
 * of the vector. The width of each element is 1 bit. The equivalent Java primitive is an int containing the value '0'
 * or '1'.
 */
public final class BitVector extends BaseDataValueVector implements FixedWidthVector {
  static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(BitVector.class);

  private final FieldReader reader = new BitReaderImpl(BitVector.this);
  private final Accessor accessor = new Accessor();
  private final Mutator mutator = new Mutator();

  private int valueCount;
  private int allocationValueCount = INITIAL_VALUE_ALLOCATION;
  private int allocationMonitor = 0;

  public BitVector(MaterializedField field, BufferAllocator allocator) {
    super(field, allocator);
  }

  @Override
  public FieldReader getReader() {
    return reader;
  }

  @Override
  public int getBufferSize() {
    return getSizeFromCount(valueCount);
  }

  private int getSizeFromCount(int valueCount) {
    return (int) Math.ceil(valueCount / 8.0);
  }

  @Override
  public int getValueCapacity() {
    return data.capacity() * 8;
  }

  private int getByteIndex(int index) {
    return (int) Math.floor(index / 8.0);
  }

  @Override
  public void setInitialCapacity(int numRecords) {
    allocationValueCount = numRecords;
  }

  public void allocateNew() {
    if (!allocateNewSafe()) {
      throw new OutOfMemoryRuntimeException();
    }
  }

  public boolean allocateNewSafe() {
    clear();
    if (allocationMonitor > 10) {
      allocationValueCount = Math.max(8, (int) (allocationValueCount / 2));
      allocationMonitor = 0;
    } else if (allocationMonitor < -2) {
      allocationValueCount = (int) (allocationValueCount * 2);
      allocationMonitor = 0;
    }

    clear();
    int valueSize = getSizeFromCount(allocationValueCount);
    DrillBuf newBuf = allocator.buffer(valueSize);
    if (newBuf == null) {
      return false;
    }

    data = newBuf;
    zeroVector();
    return true;
  }

  /**
   * Allocate a new memory space for this vector. Must be called prior to using the ValueVector.
   *
   * @param valueCount
   *          The number of values which can be contained within this vector.
   */
  public void allocateNew(int valueCount) {
    clear();
    int valueSize = getSizeFromCount(valueCount);
    DrillBuf newBuf = allocator.buffer(valueSize);
    if (newBuf == null) {
      throw new OutOfMemoryRuntimeException(String.format("Failure while allocating buffer of d% bytes.", valueSize));
    }

    data = newBuf;
    zeroVector();
  }

  /**
   * Allocate new buffer with double capacity, and copy data into the new buffer. Replace vector's buffer with new buffer, and release old one
   */
  public void reAlloc() {
    allocationValueCount *= 2;
    int valueSize = getSizeFromCount(allocationValueCount);
    DrillBuf newBuf = allocator.buffer(valueSize);
    if (newBuf == null) {
      throw new OutOfMemoryRuntimeException(String.format("Failure while allocating buffer of %d bytes.", valueSize));
    }

    newBuf.setZero(0, newBuf.capacity());
    newBuf.setBytes(0, data, 0, data.capacity());
    data.release();
    data = newBuf;
  }

  /**
   * {@inheritDoc}
   */
  @Override
  public void zeroVector() {
    data.setZero(0, data.capacity());
  }

  @Override
  public int load(int valueCount, DrillBuf buf) {
    clear();
    this.valueCount = valueCount;
    int len = getSizeFromCount(valueCount);
    data = (DrillBuf) buf.slice(0, len);
    data.retain();
    return len;
  }

  public void copyFrom(int inIndex, int outIndex, BitVector from) {
    this.mutator.set(outIndex, from.accessor.get(inIndex));
  }

  public boolean copyFromSafe(int inIndex, int outIndex, BitVector from) {
    if (outIndex >= this.getValueCapacity()) {
      decrementAllocationMonitor();
      return false;
    }
    copyFrom(inIndex, outIndex, from);
    return true;
  }

  @Override
  public void load(SerializedField metadata, DrillBuf buffer) {
    assert this.field.matches(metadata);
    int loaded = load(metadata.getValueCount(), buffer);
    assert metadata.getBufferLength() == loaded;
  }

  public Mutator getMutator() {
    return new Mutator();
  }

  public Accessor getAccessor() {
    return new Accessor();
  }

  public TransferPair getTransferPair() {
    return new TransferImpl(getField());
  }
  public TransferPair getTransferPair(FieldReference ref) {
    return new TransferImpl(getField().withPath(ref));
  }

  public TransferPair makeTransferPair(ValueVector to) {
    return new TransferImpl((BitVector) to);
  }


  public void transferTo(BitVector target) {
    target.clear();
    target.data = data;
    target.data.retain();
    target.valueCount = valueCount;
    clear();
  }

  public void splitAndTransferTo(int startIndex, int length, BitVector target) {
    assert startIndex + length <= valueCount;
    int firstByte = getByteIndex(startIndex);
    int byteSize = getSizeFromCount(length);
    int offset = startIndex % 8;
    if (offset == 0) {
      target.clear();
      // slice
      target.data = (DrillBuf) this.data.slice(firstByte, byteSize);
      target.data.retain();
    } else {
      // Copy data
      // When the first bit starts from the middle of a byte (offset != 0), copy data from src BitVector.
      // Each byte in the target is composed by a part in i-th byte, another part in (i+1)-th byte.
      // The last byte copied to target is a bit tricky :
      //   1) if length requires partly byte ( length % 8 !=0), copy the remaining bits only.
      //   2) otherwise, copy the last byte in the same way as to the prior bytes.
      target.clear();
      target.allocateNew(length);
      // TODO maybe do this one word at a time, rather than byte?
      for (int i = 0; i < byteSize - 1; i++) {
        target.data.setByte(i, (((this.data.getByte(firstByte + i) & 0xFF) >>> offset) + (this.data.getByte(firstByte + i + 1) <<  (8 - offset))));
      }
      if (length % 8 != 0) {
        target.data.setByte(byteSize - 1, ((this.data.getByte(firstByte + byteSize - 1) & 0xFF) >>> offset));
      } else {
        target.data.setByte(byteSize - 1,
            (((this.data.getByte(firstByte + byteSize - 1) & 0xFF) >>> offset) + (this.data.getByte(firstByte + byteSize) <<  (8 - offset))));
      }
    }
    target.getMutator().setValueCount(length);
  }

  private class TransferImpl implements TransferPair {
    BitVector to;

    public TransferImpl(MaterializedField field) {
      this.to = new BitVector(field, allocator);
    }

    public TransferImpl(BitVector to) {
      this.to = to;
    }

    public BitVector getTo() {
      return to;
    }

    public void transfer() {
      transferTo(to);
    }

    public void splitAndTransfer(int startIndex, int length) {
      splitAndTransferTo(startIndex, length, to);
    }

    @Override
    public void copyValueSafe(int fromIndex, int toIndex) {
      to.copyFromSafe(fromIndex, toIndex, BitVector.this);
    }
  }

  private void decrementAllocationMonitor() {
    if (allocationMonitor > 0) {
      allocationMonitor = 0;
    }
    --allocationMonitor;
  }

  private void incrementAllocationMonitor() {
    ++allocationMonitor;
  }

  public class Accessor extends BaseAccessor {

    /**
     * Get the byte holding the desired bit, then mask all other bits. Iff the result is 0, the bit was not set.
     *
     * @param index
     *          position of the bit in the vector
     * @return 1 if set, otherwise 0
     */
    public final int get(int index) {
      int byteIndex = index >> 3;
      byte b = data.getByte(byteIndex);
      int bitIndex = index & 7;
      return Long.bitCount(b &  (1L << bitIndex));
    }

    @Override
    public boolean isNull(int index) {
      return false;
    }

    @Override
    public final Boolean getObject(int index) {
      return new Boolean(get(index) != 0);
    }

    @Override
    public final int getValueCount() {
      return valueCount;
    }

    public final void get(int index, BitHolder holder) {
      holder.value = get(index);
    }

    public final void get(int index, NullableBitHolder holder) {
      holder.isSet = 1;
      holder.value = get(index);
    }
  }

  /**
   * MutableBit implements a vector of bit-width values. Elements in the vector are accessed by position from the
   * logical start of the vector. Values should be pushed onto the vector sequentially, but may be randomly accessed.
   *
   * NB: this class is automatically generated from ValueVectorTypes.tdd using FreeMarker.
   */
  public class Mutator extends BaseMutator {

    private Mutator() {
    }

    /**
     * Set the bit at the given index to the specified value.
     *
     * @param index
     *          position of the bit to set
     * @param value
     *          value to set (either 1 or 0)
     */
    public final void set(int index, int value) {
      int byteIndex = index >> 3;
      int bitIndex = index & 7;
      byte currentByte = data.getByte(byteIndex);
      byte bitMask = (byte) (1L << bitIndex);
      if (value != 0) {
        currentByte |= bitMask;
      } else {
        currentByte -= (bitMask & currentByte);
      }

      data.setByte(byteIndex, currentByte);
    }

    public final void set(int index, BitHolder holder) {
      set(index, holder.value);
    }

    final void set(int index, NullableBitHolder holder) {
      set(index, holder.value);
    }

    public void setSafe(int index, int value) {
      while(index >= getValueCapacity()) {
        reAlloc();
      }
      set(index, value);
    }

    public void setSafe(int index, BitHolder holder) {
      while(index >= getValueCapacity()) {
        reAlloc();
      }
      set(index, holder.value);
    }

    public void setSafe(int index, NullableBitHolder holder) {
      while(index >= getValueCapacity()) {
        reAlloc();
      }
      set(index, holder.value);
    }

    public final void setValueCount(int valueCount) {
      int currentValueCapacity = getValueCapacity();
      BitVector.this.valueCount = valueCount;
      int idx = getSizeFromCount(valueCount);
      while(valueCount > getValueCapacity()) {
        reAlloc();
      }
      if (valueCount > 0 && currentValueCapacity > valueCount * 2) {
        incrementAllocationMonitor();
      } else if (allocationMonitor > 0) {
        allocationMonitor = 0;
      }
      VectorTrimmer.trim(data, idx);
    }

    @Override
    public final void generateTestData(int values) {
      boolean even = true;
      for (int i = 0; i < values; i++, even = !even) {
        if (even) {
          set(i, 1);
        }
      }
      setValueCount(values);
    }

  }

}


File: exec/java-exec/src/test/java/org/apache/drill/exec/record/vector/TestValueVector.java
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.apache.drill.exec.record.vector;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.nio.charset.Charset;

import org.apache.drill.common.expression.SchemaPath;
import org.apache.drill.exec.ExecTest;
import org.apache.drill.exec.expr.TypeHelper;
import org.apache.drill.exec.expr.holders.BitHolder;
import org.apache.drill.exec.expr.holders.IntHolder;
import org.apache.drill.exec.expr.holders.NullableFloat4Holder;
import org.apache.drill.exec.expr.holders.NullableUInt4Holder;
import org.apache.drill.exec.expr.holders.NullableVar16CharHolder;
import org.apache.drill.exec.expr.holders.NullableVarCharHolder;
import org.apache.drill.exec.expr.holders.RepeatedFloat4Holder;
import org.apache.drill.exec.expr.holders.RepeatedVarBinaryHolder;
import org.apache.drill.exec.expr.holders.UInt4Holder;
import org.apache.drill.exec.expr.holders.VarCharHolder;
import org.apache.drill.exec.memory.TopLevelAllocator;
import org.apache.drill.exec.record.MaterializedField;
import org.apache.drill.exec.vector.BitVector;
import org.apache.drill.exec.vector.NullableFloat4Vector;
import org.apache.drill.exec.vector.NullableUInt4Vector;
import org.apache.drill.exec.vector.NullableVarCharVector;
import org.apache.drill.exec.vector.UInt4Vector;
import org.apache.drill.exec.vector.ValueVector;
import org.apache.drill.exec.vector.complex.MapVector;
import org.apache.drill.exec.vector.complex.RepeatedListVector;
import org.apache.drill.exec.vector.complex.RepeatedMapVector;
import org.junit.Test;

public class TestValueVector extends ExecTest {
  private final static SchemaPath EMPTY_SCHEMA_PATH = SchemaPath.getSimplePath("");

  private final static byte[] STR1 = new String("AAAAA1").getBytes(Charset.forName("UTF-8"));
  private final static byte[] STR2 = new String("BBBBBBBBB2").getBytes(Charset.forName("UTF-8"));
  private final static byte[] STR3 = new String("CCCC3").getBytes(Charset.forName("UTF-8"));

  TopLevelAllocator allocator = new TopLevelAllocator();

  @Test
  public void testFixedType() {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, UInt4Holder.TYPE);

    // Create a new value vector for 1024 integers
    UInt4Vector v = new UInt4Vector(field, allocator);
    UInt4Vector.Mutator m = v.getMutator();
    v.allocateNew(1024);

    // Put and set a few values
    m.setSafe(0, 100);
    m.setSafe(1, 101);
    m.setSafe(100, 102);
    m.setSafe(1022, 103);
    m.setSafe(1023, 104);
    assertEquals(100, v.getAccessor().get(0));
    assertEquals(101, v.getAccessor().get(1));
    assertEquals(102, v.getAccessor().get(100));
    assertEquals(103, v.getAccessor().get(1022));
    assertEquals(104, v.getAccessor().get(1023));

  }

  @Test
  public void testNullableVarLen2() {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, NullableVarCharHolder.TYPE);

    // Create a new value vector for 1024 integers
    NullableVarCharVector v = new NullableVarCharVector(field, allocator);
    NullableVarCharVector.Mutator m = v.getMutator();
    v.allocateNew(1024*10, 1024);

    m.set(0, STR1);
    m.set(1, STR2);
    m.set(2, STR3);

    // Check the sample strings
    assertArrayEquals(STR1, v.getAccessor().get(0));
    assertArrayEquals(STR2, v.getAccessor().get(1));
    assertArrayEquals(STR3, v.getAccessor().get(2));

    // Ensure null value throws
    boolean b = false;
    try {
      v.getAccessor().get(3);
    } catch(IllegalStateException e) {
      b = true;
    }finally{
      assertTrue(b);
    }

  }


  @Test
  public void testNullableFixedType() {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, NullableUInt4Holder.TYPE);

    // Create a new value vector for 1024 integers
    NullableUInt4Vector v = new NullableUInt4Vector(field, allocator);
    NullableUInt4Vector.Mutator m = v.getMutator();
    v.allocateNew(1024);

    // Put and set a few values
    m.set(0, 100);
    m.set(1, 101);
    m.set(100, 102);
    m.set(1022, 103);
    m.set(1023, 104);
    assertEquals(100, v.getAccessor().get(0));
    assertEquals(101, v.getAccessor().get(1));
    assertEquals(102, v.getAccessor().get(100));
    assertEquals(103, v.getAccessor().get(1022));
    assertEquals(104, v.getAccessor().get(1023));

    // Ensure null values throw
    {
      boolean b = false;
      try {
        v.getAccessor().get(3);
      } catch(IllegalStateException e) {
        b = true;
      }finally{
        assertTrue(b);
      }
    }


    v.allocateNew(2048);
    {
      boolean b = false;
      try {
        v.getAccessor().get(0);
      } catch(IllegalStateException e) {
        b = true;
      }finally{
        assertTrue(b);
      }
    }

    m.set(0, 100);
    m.set(1, 101);
    m.set(100, 102);
    m.set(1022, 103);
    m.set(1023, 104);
    assertEquals(100, v.getAccessor().get(0));
    assertEquals(101, v.getAccessor().get(1));
    assertEquals(102, v.getAccessor().get(100));
    assertEquals(103, v.getAccessor().get(1022));
    assertEquals(104, v.getAccessor().get(1023));

    // Ensure null values throw

    {
      boolean b = false;
      try {
        v.getAccessor().get(3);
      } catch(IllegalStateException e) {
        b = true;
      }finally{
        assertTrue(b);
      }
    }

  }

  @Test
  public void testNullableFloat() {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, NullableFloat4Holder.TYPE);

    // Create a new value vector for 1024 integers
    NullableFloat4Vector v = (NullableFloat4Vector) TypeHelper.getNewVector(field, allocator);
    NullableFloat4Vector.Mutator m = v.getMutator();
    v.allocateNew(1024);

    // Put and set a few values
    m.set(0, 100.1f);
    m.set(1, 101.2f);
    m.set(100, 102.3f);
    m.set(1022, 103.4f);
    m.set(1023, 104.5f);
    assertEquals(100.1f, v.getAccessor().get(0), 0);
    assertEquals(101.2f, v.getAccessor().get(1), 0);
    assertEquals(102.3f, v.getAccessor().get(100), 0);
    assertEquals(103.4f, v.getAccessor().get(1022), 0);
    assertEquals(104.5f, v.getAccessor().get(1023), 0);

    // Ensure null values throw
    {
      boolean b = false;
      try {
        v.getAccessor().get(3);
      } catch(IllegalStateException e) {
        b = true;
      }finally{
        assertTrue(b);
      }
    }

    v.allocateNew(2048);
    {
      boolean b = false;
      try {
        v.getAccessor().get(0);
      } catch(IllegalStateException e) {
        b = true;
      }finally{
        assertTrue(b);
      }
    }
  }

  @Test
  public void testBitVector() {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, BitHolder.TYPE);

    // Create a new value vector for 1024 integers
    BitVector v = new BitVector(field, allocator);
    BitVector.Mutator m = v.getMutator();
    v.allocateNew(1024);

    // Put and set a few values
    m.set(0, 1);
    m.set(1, 0);
    m.set(100, 0);
    m.set(1022, 1);
    assertEquals(1, v.getAccessor().get(0));
    assertEquals(0, v.getAccessor().get(1));
    assertEquals(0, v.getAccessor().get(100));
    assertEquals(1, v.getAccessor().get(1022));

    // test setting the same value twice
    m.set(0, 1);
    m.set(0, 1);
    m.set(1, 0);
    m.set(1, 0);
    assertEquals(1, v.getAccessor().get(0));
    assertEquals(0, v.getAccessor().get(1));

    // test toggling the values
    m.set(0, 0);
    m.set(1, 1);
    assertEquals(0, v.getAccessor().get(0));
    assertEquals(1, v.getAccessor().get(1));

    // Ensure unallocated space returns 0
    assertEquals(0, v.getAccessor().get(3));
  }


  @Test
  public void testReAllocNullableFixedWidthVector() throws Exception {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, NullableFloat4Holder.TYPE);

    // Create a new value vector for 1024 integers
    NullableFloat4Vector v = (NullableFloat4Vector) TypeHelper.getNewVector(field, allocator);
    NullableFloat4Vector.Mutator m = v.getMutator();
    v.allocateNew(1024);

    assertEquals(1024, v.getValueCapacity());

    // Put values in indexes that fall within the initial allocation
    m.setSafe(0, 100.1f);
    m.setSafe(100, 102.3f);
    m.setSafe(1023, 104.5f);

    // Now try to put values in space that falls beyond the initial allocation
    m.setSafe(2000, 105.5f);

    // Check valueCapacity is more than initial allocation
    assertEquals(1024*2, v.getValueCapacity());

    assertEquals(100.1f, v.getAccessor().get(0), 0);
    assertEquals(102.3f, v.getAccessor().get(100), 0);
    assertEquals(104.5f, v.getAccessor().get(1023), 0);
    assertEquals(105.5f, v.getAccessor().get(2000), 0);


    // Set the valueCount to be more than valueCapacity of current allocation. This is possible for NullableValueVectors
    // as we don't call setSafe for null values, but we do call setValueCount when all values are inserted into the
    // vector
    m.setValueCount(v.getValueCapacity() + 200);
  }

  @Test
  public void testReAllocNullableVariableWidthVector() throws Exception {
    MaterializedField field = MaterializedField.create(EMPTY_SCHEMA_PATH, NullableVarCharHolder.TYPE);

    // Create a new value vector for 1024 integers
    NullableVarCharVector v = (NullableVarCharVector) TypeHelper.getNewVector(field, allocator);
    NullableVarCharVector.Mutator m = v.getMutator();
    v.allocateNew();

    int initialCapacity = v.getValueCapacity();

    // Put values in indexes that fall within the initial allocation
    m.setSafe(0, STR1, 0, STR1.length);
    m.setSafe(initialCapacity - 1, STR2, 0, STR2.length);

    // Now try to put values in space that falls beyond the initial allocation
    m.setSafe(initialCapacity + 200, STR3, 0, STR3.length);

    // Check valueCapacity is more than initial allocation
    assertEquals((initialCapacity+1)*2-1, v.getValueCapacity());

    assertArrayEquals(STR1, v.getAccessor().get(0));
    assertArrayEquals(STR2, v.getAccessor().get(initialCapacity-1));
    assertArrayEquals(STR3, v.getAccessor().get(initialCapacity + 200));

    // Set the valueCount to be more than valueCapacity of current allocation. This is possible for NullableValueVectors
    // as we don't call setSafe for null values, but we do call setValueCount when the current batch is processed.
    m.setValueCount(v.getValueCapacity() + 200);
  }

  @Test
  public void testVVInitialCapacity() {
    final MaterializedField[] fields = new MaterializedField[9];
    final ValueVector[] valueVectors = new ValueVector[9];

    fields[0] = MaterializedField.create(EMPTY_SCHEMA_PATH, BitHolder.TYPE);
    fields[1] = MaterializedField.create(EMPTY_SCHEMA_PATH, IntHolder.TYPE);
    fields[2] = MaterializedField.create(EMPTY_SCHEMA_PATH, VarCharHolder.TYPE);
    fields[3] = MaterializedField.create(EMPTY_SCHEMA_PATH, NullableVar16CharHolder.TYPE);
    fields[4] = MaterializedField.create(EMPTY_SCHEMA_PATH, RepeatedFloat4Holder.TYPE);
    fields[5] = MaterializedField.create(EMPTY_SCHEMA_PATH, RepeatedVarBinaryHolder.TYPE);

    fields[6] = MaterializedField.create(EMPTY_SCHEMA_PATH, MapVector.TYPE);
    fields[6].addChild(fields[0] /*bit*/);
    fields[6].addChild(fields[2] /*varchar*/);

    fields[7] = MaterializedField.create(EMPTY_SCHEMA_PATH, RepeatedMapVector.TYPE);
    fields[7].addChild(fields[1] /*int*/);
    fields[7].addChild(fields[3] /*optional var16char*/);

    fields[8] = MaterializedField.create(EMPTY_SCHEMA_PATH, RepeatedListVector.TYPE);
    fields[8].addChild(fields[1] /*int*/);

    final int initialCapacity = 1024;

    for(int i=0; i<valueVectors.length; i++) {
      valueVectors[i] = TypeHelper.getNewVector(fields[i], allocator);
      valueVectors[i].setInitialCapacity(initialCapacity);
      valueVectors[i].allocateNew();
    }

    for(int i=0; i<valueVectors.length; i++) {
      final ValueVector vv = valueVectors[i];
      final int vvCapacity = vv.getValueCapacity();
      assertEquals(String.format("Incorrect value capacity for %s [%d]", vv.getField(), vvCapacity),
          initialCapacity, vvCapacity);
    }
  }
}
