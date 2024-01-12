Refactoring Types: ['Extract Method']
mps/text/impl/TextGenSupport.java
/*
 * Copyright 2003-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package jetbrains.mps.text.impl;

import jetbrains.mps.smodel.DynamicReference;
import jetbrains.mps.text.TextArea;
import jetbrains.mps.text.TextMark;
import jetbrains.mps.text.rt.TextGenContext;
import jetbrains.mps.textGen.TextGen;
import jetbrains.mps.textGen.TextGenBuffer;
import jetbrains.mps.textGen.TextGenRegistry;
import jetbrains.mps.textGen.TraceInfoGenerationUtil;
import jetbrains.mps.textgen.trace.ScopePositionInfo;
import jetbrains.mps.textgen.trace.TraceablePositionInfo;
import jetbrains.mps.textgen.trace.UnitPositionInfo;
import jetbrains.mps.util.SNodeOperations;
import jetbrains.mps.util.annotation.ToRemove;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.mps.openapi.model.SModelReference;
import org.jetbrains.mps.openapi.model.SNode;
import org.jetbrains.mps.openapi.model.SReference;

import java.util.List;

/**
 * Facility to keep implementation methods I don't want to get exposed in TextGenDescriptorBase or elsewhere deemed API.
 * Besides it helps to keep state of the {@link jetbrains.mps.text.rt.TextGenDescriptor#generateText(TextGenContext)} invocation
 * context and to shorten argument list of utility methods.
 * Generated code shall use this class to perform various operations that are not straightforward enough to get generated
 * right into <code>TextGenDescriptor</code>.
 * @author Artem Tikhomirov
 */
public final class TextGenSupport implements TextArea {
  private final TextGenContext myContext;
  private final TraceInfoCollector myTraceInfoCollector;

  public TextGenSupport(@NotNull TextGenContext context) {
    myContext = context;
    final TextGenBuffer buffer = ((TextGenTransitionContext) context).getLegacyBuffer();
    myTraceInfoCollector = TraceInfoGenerationUtil.getTraceInfoCollector(buffer);
  }

  public boolean needPositions() {
    return getTraceInfoCollector() != null;
  }

  public void createPositionInfo() {
    if (needPositions()) {
      myContext.getBuffer().pushMark();
    }
  }

  public void createScopeInfo( ) {
    if (needPositions()) {
      myContext.getBuffer().pushMark();
    }
  }

  public void createUnitInfo() {
    if (needPositions()) {
      myContext.getBuffer().pushMark();
    }
  }

  public void fillPositionInfo(String propertyString) {
    final TraceInfoCollector tic = getTraceInfoCollector();
    if (tic == null) {
      return;
    }
    TextMark m = myContext.getBuffer().popMark();
    final TraceablePositionInfo pi = tic.createTracePosition(m, myContext.getPrimaryInput());
    pi.setPropertyString(propertyString);
  }

  public void fillScopeInfo(List<SNode> vars) {
    final TraceInfoCollector tic = getTraceInfoCollector();
    if (tic == null) {
      return;
    }
    TextMark m = myContext.getBuffer().popMark();
    final ScopePositionInfo pi = tic.createScopePosition(m, myContext.getPrimaryInput());
    for (SNode var : vars) {
      if (var != null) {
        pi.addVarInfo(var);
      }
    }
  }

  public void fillUnitInfo(String unitName) {
    final TraceInfoCollector tic = getTraceInfoCollector();
    if (tic == null) {
      return;
    }
    TextMark m = myContext.getBuffer().popMark();
    final UnitPositionInfo pi = tic.createUnitPosition(m, myContext.getPrimaryInput());
    pi.setUnitName(unitName);
    TraceInfoGenerationUtil.warnIfUnitNameInvalid(unitName, myContext.getPrimaryInput());
  }

  private TraceInfoCollector getTraceInfoCollector() {
    return myTraceInfoCollector;
  }

  public void appendNode(SNode node) {
    final TextGenBuffer buffer = getLegacyBuffer();
    TextGenRegistry.getInstance().getTextGenDescriptor(node).generateText(new TextGenTransitionContext(node, buffer));
  }

  // FIXME copy of SNodeTextGen.foundError()
  public void reportError(String info) {
    String message = info != null ?
        "textgen error: '" + info + "' in " + SNodeOperations.getDebugText(myContext.getPrimaryInput()) :
        "textgen error in " + SNodeOperations.getDebugText(myContext.getPrimaryInput());
    getLegacyBuffer().foundError(message, myContext.getPrimaryInput(), null);
  }

  // FIXME copy of SNodeTextGen.setEncoding()
  public void setEncoding(@Nullable String encoding) {
    getLegacyBuffer().putUserObject(TextGen.OUTPUT_ENCODING, encoding);
  }

  // FIXME copy of SNodeTextGen.getReferentPresentation(), slightly modified to drop dead code branches
  public void appendReferentText(SReference reference) {
    if (reference == null) {
      reportError("null reference");
      append("<err:null reference>");
      return;
    }

    String shortName;
    if (reference instanceof DynamicReference) {
      shortName = ((DynamicReference) reference).getResolveInfo();
      if (shortName.startsWith("[")) {
        // todo: hack, remove with [] removing
        shortName = shortName.substring(shortName.lastIndexOf("]") + 1).trim();
      } else {
        final SModelReference modelReference = reference.getTargetSModelReference();
        if (modelReference == null) {
          int lastDot = shortName.lastIndexOf('.');
          if (lastDot >= 0) {
            shortName = shortName.substring(lastDot + 1);
            if (shortName.indexOf('$') >= 0) {
              shortName = shortName.replace('$', '.');
            }
          }
        }
      }
    } else {
      SNode targetNode = reference.getTargetNode();
      if (targetNode == null) {
        reportError(String.format("Unknown target for role %s", reference.getRole()));
        append("???");
        return;
      }
      shortName = jetbrains.mps.util.SNodeOperations.getResolveInfo(targetNode);
    }
    append(shortName);
  }

  // For compatibility with code that uses TextGenBuffer through 'buffer' concept function parameter
  @ToRemove(version = 3.3)
  public TextGenBuffer getLegacyBuffer() {
    return ((TextGenTransitionContext) myContext).getLegacyBuffer();
  }

  ////////////
  // TextArea. Simply delegate to whatever actual text area of the buffer is.

  @Override
  public TextArea append(CharSequence text) {
    return myContext.getBuffer().area().append(text);
  }

  @Override
  public TextArea newLine() {
    return myContext.getBuffer().area().newLine();
  }

  @Override
  public TextArea indent() {
    return myContext.getBuffer().area().indent();
  }

  @Override
  public TextArea increaseIndent() {
    return myContext.getBuffer().area().increaseIndent();
  }

  @Override
  public TextArea decreaseIndent() {
    return myContext.getBuffer().area().decreaseIndent();
  }

  @Override
  public int length() {
    return myContext.getBuffer().area().length();
  }
}


File: core/textgen/source/jetbrains/mps/text/rt/BaseTextGenAspectDescriptor.java
/*
 * Copyright 2003-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package jetbrains.mps.text.rt;

/**
 * Base implementation of {@link TextGenAspectDescriptor} to extend from generated code
 * @author Artem Tikhomirov
 * @since 3.3
 */
public abstract class BaseTextGenAspectDescriptor extends TextGenAspectBase {
}


File: core/textgen/source/jetbrains/mps/textGen/TextGen.java
/*
 * Copyright 2003-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package jetbrains.mps.textGen;

import jetbrains.mps.messages.IMessage;
import jetbrains.mps.messages.Message;
import jetbrains.mps.messages.MessageKind;
import jetbrains.mps.text.BufferSnapshot;
import jetbrains.mps.text.MissingTextGenDescriptor;
import jetbrains.mps.text.impl.TextGenTransitionContext;
import jetbrains.mps.text.impl.TraceInfoCollector;
import jetbrains.mps.text.rt.TextGenDescriptor;
import jetbrains.mps.textgen.trace.ScopePositionInfo;
import jetbrains.mps.textgen.trace.TraceablePositionInfo;
import jetbrains.mps.textgen.trace.UnitPositionInfo;
import jetbrains.mps.util.EncodingUtil;
import jetbrains.mps.util.NameUtil;
import jetbrains.mps.util.annotation.ToRemove;
import org.apache.log4j.Logger;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.mps.openapi.model.SNode;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * @deprecated Use {@link jetbrains.mps.text.TextGeneratorEngine} to produce text from models.
 * There's yet no alternative to transform single node to text, FIXME shall implement
 */
@Deprecated
@ToRemove(version = 3.3)
public class TextGen {
  public static final String PACKAGE_NAME = "PACKAGE_NAME";
  public static final String DEPENDENCY = "DEPENDENCY";
  public static final String EXTENDS = "EXTENDS";
  public static final String OUTPUT_ENCODING = "OUTPUT_ENCODING";
  public static final String ROOT_NODE = "ROOT_NODE";

  public static final String NO_TEXTGEN = "\33\33NO TEXTGEN\33\33";

  // api
  public static TextGenerationResult generateText(SNode node) {
    return generateText(node, false, false, null);
  }

  public static boolean canGenerateTextFor(SNode node) {
    return !(getTextGenForNode(node) instanceof MissingTextGenDescriptor);
  }

  public static String getExtension(@NotNull SNode node) {
    return getLegacyTextGen(node).getExtension(node);
  }

  public static String getFileName(@NotNull SNode node) {
    final SNodeTextGen tg = getLegacyTextGen(node);
    String fname = tg.getFilename(node);
    String extension = tg.getExtension(node);
    return (extension == null) ? fname : fname + '.' + extension;
  }

  public static TextGenerationResult generateText(SNode node, boolean failIfNoTextgen, boolean withDebugInfo, @Nullable StringBuilder[] buffers) {
    if (canGenerateTextFor(node)) {
      return generateText(node, withDebugInfo, buffers);
    } else if (failIfNoTextgen) {
      String error = "Can't generate text from " + node;
      Message m = new Message(MessageKind.ERROR, error);
      if (node != null) {
        m.setHintObject(node.getReference());
      }
      return new TextGenerationResult(node, NO_TEXTGEN, true, Collections.<IMessage>singleton(m), null, null, null, null);
    } else {
      return new TextGenerationResult(node, NO_TEXTGEN, false, Collections.<IMessage>emptyList(), null, null, null, null);
    }
  }

  public static TextGenerationResult generateText(SNode node, boolean withDebugInfo, @Nullable StringBuilder[] buffers) {
    TextGenBuffer buffer = new TextGenBuffer(withDebugInfo, buffers);
    buffer.putUserObject(PACKAGE_NAME, jetbrains.mps.util.SNodeOperations.getModelLongName(node.getModel()));
    buffer.putUserObject(ROOT_NODE, node);
    final TraceInfoCollector tic;
    if (withDebugInfo)  {
      tic = new TraceInfoCollector();
      TraceInfoGenerationUtil.setTraceInfoCollector(buffer, tic);
    } else {
      tic = null;
    }

    appendNodeText(buffer, node);

    // position info
    Map<SNode, TraceablePositionInfo> positionInfo = null;
    Map<SNode, ScopePositionInfo> scopeInfo = null;
    Map<SNode, UnitPositionInfo> unitInfo = null;
    final BufferSnapshot textSnapshot = buffer.getTextSnapshot();
    if (tic != null) {
      tic.populatePositions(textSnapshot);
      //
      positionInfo = tic.getTracePositions();
      scopeInfo = tic.getScopePositions();
      unitInfo = tic.getUnitPositions();
    }

    // dependencies
    List<String> dependencies = getUserObjectCollection(DEPENDENCY, node, buffer, (Set<String>) buffer.getUserObject(EXTENDS));
    List<String> extend = getUserObjectCollection(EXTENDS, node, buffer, null);

    Map<String, List<String>> deps = new HashMap<String, List<String>>(2);
    deps.put(DEPENDENCY, dependencies);
    deps.put(EXTENDS, extend);

    final String bufferOutcome = textSnapshot.getText().toString();
    Object result = bufferOutcome;
    String outputEncoding = (String) buffer.getUserObject(OUTPUT_ENCODING);
    if (outputEncoding != null) {
      if (outputEncoding.equals("binary")) {
        result = EncodingUtil.decodeBase64(bufferOutcome);
      } else {
        try {
          result = EncodingUtil.encode(bufferOutcome, outputEncoding);
        } catch (IOException ex) {
          buffer.foundError("cannot encode the output stream", null, ex);
        }
      }
    }
    return new TextGenerationResult(node, result, buffer.hasErrors(), buffer.problems(), positionInfo, scopeInfo, unitInfo, deps);
  }

  private static void appendNodeText(TextGenBuffer buffer, SNode node) {
    if (node == null) {
      buffer.append("???");
      return;
    }

    getTextGenForNode(node).generateText(new TextGenTransitionContext(node, buffer));
  }

  // helper stuff
  @NotNull
  /*package*/ static TextGenDescriptor getTextGenForNode(@NotNull SNode node) {
    return TextGenRegistry.getInstance().getTextGenDescriptor(node);
  }

  // compatibility code until TextUnit and code to break input model into these units, with filename assigned, are introduced.
  private static SNodeTextGen getLegacyTextGen(@NotNull SNode node) {
    try {
      Class<? extends SNodeTextGen> textgenClass = TextGenRegistry.getInstance().getLegacyTextGenClass(node.getConcept());
      if (textgenClass != null && SNodeTextGen.class.isAssignableFrom(textgenClass)) {
        return textgenClass.newInstance();
      }
    } catch (InstantiationException ex) {
      Logger.getLogger(TextGen.class).error("Failed to instantiate textgen", ex);
      // fall-through
    } catch (IllegalAccessException ex) {
      Logger.getLogger(TextGen.class).error("Failed to instantiate textgen", ex);
      // fall-through
    }
    return new DefaultTextGen();
  }

  private static List<String> getUserObjectCollection(String key, SNode node, TextGenBuffer buffer, Set<String> skipSet) {
    Set<String> dependenciesObject = (Set<String>) buffer.getUserObject(key);
    final String nodeFQName = NameUtil.nodeFQName(node);
    if (dependenciesObject != null) {
      List<String> dependencies = new ArrayList<String>(dependenciesObject.size());
      for (String dependObj : dependenciesObject) {
        if (dependObj == null || nodeFQName.equals(dependObj)) {
          continue;
        }
        if (skipSet != null && skipSet.contains(dependObj)) {
          continue;
        }
        dependencies.add(dependObj);
      }
      Collections.sort(dependencies);
      return dependencies;
    }
    return Collections.emptyList();
  }
}


File: core/textgen/source/jetbrains/mps/textGen/TextGenRegistry.java
/*
 * Copyright 2003-2015 JetBrains s.r.o.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package jetbrains.mps.textGen;

import jetbrains.mps.components.CoreComponent;
import jetbrains.mps.smodel.Language;
import jetbrains.mps.smodel.LanguageAspect;
import jetbrains.mps.smodel.ModelDependencyScanner;
import jetbrains.mps.smodel.ModuleRepositoryFacade;
import jetbrains.mps.smodel.SNodeUtil;
import jetbrains.mps.smodel.adapter.ids.MetaIdHelper;
import jetbrains.mps.smodel.language.LanguageRegistry;
import jetbrains.mps.smodel.language.LanguageRegistryListener;
import jetbrains.mps.smodel.language.LanguageRuntime;
import jetbrains.mps.smodel.structure.DescriptorUtils;
import jetbrains.mps.text.LegacyTextGenAdapter;
import jetbrains.mps.text.MissingTextGenDescriptor;
import jetbrains.mps.text.rt.TextGenAspectDescriptor;
import jetbrains.mps.text.rt.TextGenDescriptor;
import jetbrains.mps.util.annotation.ToRemove;
import org.apache.log4j.Logger;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.jetbrains.mps.openapi.language.SConcept;
import org.jetbrains.mps.openapi.language.SLanguage;
import org.jetbrains.mps.openapi.model.SModel;
import org.jetbrains.mps.openapi.model.SNode;
import org.jetbrains.mps.util.ImmediateParentConceptIterator;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Excerpt from ConceptRegistry related to TextGenDescriptor.
 * It's artifact of refactoring to break [textgen] and [kernel] cycle dependency.
 * FIXME For the time being, it's initialized together with ConceptRegistry from MPSCore, though shall be separate ComponentPlugin,
 * like MPSGenerator, and initialized from MPSCoreComponents and alike.
 * @author Artem Tikhomirov
 */
public class TextGenRegistry implements CoreComponent, LanguageRegistryListener {
  private static TextGenRegistry INSTANCE;

  private final Map<String, TextGenDescriptor> textGenDescriptors = new ConcurrentHashMap<String, TextGenDescriptor>();
  private final LanguageRegistry myLanguageRegistry;

  // FIXME shall be package-local once we have distinct MPSTextGen ComponentPlugin
  public TextGenRegistry(@NotNull LanguageRegistry languageRegistry) {
    myLanguageRegistry = languageRegistry;
  }

  @Override
  public void init() {
    if (INSTANCE != null) {
      throw new IllegalStateException("double initialization");
    }
    INSTANCE = this;
    myLanguageRegistry.addRegistryListener(this);
  }

  @Override
  public void dispose() {
    myLanguageRegistry.removeRegistryListener(this);
    INSTANCE = null;
  }

  public static TextGenRegistry getInstance() {
    return INSTANCE;
  }

  @NotNull
  public TextGenDescriptor getTextGenDescriptor(@Nullable SNode node) {
    if (node == null) {
      // FIXME default implementation doesn't expect null node
      return new MissingTextGenDescriptor();
    }
    return getTextGenDescriptor(node.getConcept());
  }

  private TextGenDescriptor getTextGenDescriptor(SConcept concept) {
    final String fqName = concept.getQualifiedName();

    TextGenDescriptor descriptor = textGenDescriptors.get(fqName);

    if (descriptor != null) {
      return descriptor;
    }

    // Would be nice if TGAD could answer for any subtype from the same language, i.e. when there's TextGen for A,
    // and there's B extends A, and we ask for B's textgen, TGAD might answer with A's right away. Then, we could
    // ask each language only once
    // TODO  HashSet<SLanguage> seen = new HashSet<SLanguage>();
    for (SConcept next : new ImmediateParentConceptIterator(concept, SNodeUtil.concept_BaseConcept)) {
      TextGenAspectDescriptor textGenAspectDescriptor = getAspect(next);
      if (textGenAspectDescriptor == null) {
        continue;
      }
      descriptor = textGenAspectDescriptor.getDescriptor(MetaIdHelper.getConcept(next));
      if (descriptor != null) {
        break;
      }
    }

    if (descriptor == null) {
      // fall-back solution for Language classes generated in previous MPS version. They don't answer for new TextGenAspectDescriptor,
      // thus we use logic extracted from TextGenAspectInterpreted, modified to use contemporary TextGenDescriptor.
      final Class<? extends SNodeTextGen> legacyTextGenClass = getLegacyTextGenClass(concept);
      if (legacyTextGenClass != null) {
        return new LegacyTextGenAdapter(legacyTextGenClass);
      }
      descriptor = new MissingTextGenDescriptor();
    }

    textGenDescriptors.put(fqName, descriptor);

    return descriptor;
  }

  @Nullable
  private TextGenAspectDescriptor getAspect(SConcept concept) {
    LanguageRuntime languageRuntime = myLanguageRegistry.getLanguage(concept.getLanguage());
    if (languageRuntime == null) {
      // Then language was just renamed and was not re-generated then it can happen that it has no
      Logger.getLogger(TextGenRegistry.class).warn(String.format("No language for concept %s, while looking for textgen descriptor.", concept));
      return null;
    } else {
      return languageRuntime.getAspect(TextGenAspectDescriptor.class);
    }
  }

  /**
   * @deprecated fall-back, to deal with Language classes generated in previous MPS version and support textgen without need to re-generate a language
   */
  @Deprecated
  @ToRemove(version = 3.3)
  public Class<? extends SNodeTextGen> getLegacyTextGenClass(SConcept c) {
    for (SConcept next : new ImmediateParentConceptIterator(c, SNodeUtil.concept_BaseConcept)) {
      String languageName = next.getLanguage().getQualifiedName();
      Language l = ModuleRepositoryFacade.getInstance().getModule(languageName, Language.class);
      String textgenClassname = LanguageAspect.TEXT_GEN.getAspectQualifiedClassName(next) + "_TextGen";
      Class<? extends SNodeTextGen> textgenClass = DescriptorUtils.getClassFromLanguage(textgenClassname, l);
      if (textgenClass != null) {
        return textgenClass;
      }
    }
    return null;
  }

  /**
   * @param model model to generate text from
   * @return aspect runtime instances for all languages involved
   */
  @NotNull
  public Collection<TextGenAspectDescriptor> getAspects(@NotNull SModel model) {
    // FIXME likely, shall collect all extended languages as well, as there might be instances of a language without textgen in the model,
    // while textgen elements are derived from extended language. HOWEVER, need to process breakdownToTextUnits carefully, so that default
    // file-per-root breakdown doesn't create duplicates!
    ArrayList<TextGenAspectDescriptor> rv = new ArrayList<TextGenAspectDescriptor>(5);
    final ModelDependencyScanner modelScanner = new ModelDependencyScanner();
    modelScanner.crossModelReferences(false).usedLanguages(true).walk(model);
    for (SLanguage l : modelScanner.getUsedLanguages()) {
      final LanguageRuntime lr = myLanguageRegistry.getLanguage(l);
      if (lr == null) {
        // XXX shall report missing language?
        continue;
      }
      final TextGenAspectDescriptor rtAspect = lr.getAspect(TextGenAspectDescriptor.class);
      if (rtAspect != null) {
        rv.add(rtAspect);
      }
    }
    return rv;
  }

  @Override
  public void beforeLanguagesUnloaded(Iterable<LanguageRuntime> languages) {
    // @see ConceptRegistry#beforeLanguagesUnloaded
  }

  @Override
  public void afterLanguagesLoaded(Iterable<LanguageRuntime> languages) {
    textGenDescriptors.clear();
  }

}


File: languages/languageDesign/textGen/source_gen/jetbrains/mps/lang/textGen/behavior/BehaviorAspectDescriptor.java
package jetbrains.mps.lang.textGen.behavior;

/*Generated by MPS */

import jetbrains.mps.smodel.runtime.BehaviorDescriptor;
import java.util.Arrays;
import jetbrains.mps.smodel.runtime.interpreted.BehaviorAspectInterpreted;

public class BehaviorAspectDescriptor implements jetbrains.mps.smodel.runtime.BehaviorAspectDescriptor {
  public BehaviorAspectDescriptor() {
  }
  public BehaviorDescriptor getDescriptor(String fqName) {
    switch (Arrays.binarySearch(stringSwitchCases_846f5o_a0a0b, fqName)) {
      case 3:
        return new ConceptTextGenDeclaration_BehaviorDescriptor();
      case 18:
        return new NodeParameter_BehaviorDescriptor();
      case 12:
        return new GenerateTextDeclaration_BehaviorDescriptor();
      case 13:
        return new IncreaseDepthOperation_BehaviorDescriptor();
      case 6:
        return new DecreaseDepthOperation_BehaviorDescriptor();
      case 14:
        return new IndentBufferOperation_BehaviorDescriptor();
      case 15:
        return new LanguageTextGenDeclaration_BehaviorDescriptor();
      case 20:
        return new OperationDeclaration_BehaviorDescriptor();
      case 19:
        return new OperationCall_BehaviorDescriptor();
      case 5:
        return new ContextParameter_BehaviorDescriptor();
      case 1:
        return new BufferParameter_BehaviorDescriptor();
      case 24:
        return new UtilityMethodDeclaration_BehaviorDescriptor();
      case 23:
        return new UtilityMethodCall_BehaviorDescriptor();
      case 11:
        return new FoundErrorOperation_BehaviorDescriptor();
      case 25:
        return new WithIndentOperation_BehaviorDescriptor();
      case 16:
        return new NewLineAppendPart_BehaviorDescriptor();
      case 17:
        return new NodeAppendPart_BehaviorDescriptor();
      case 2:
        return new CollectionAppendPart_BehaviorDescriptor();
      case 4:
        return new ConstantStringAppendPart_BehaviorDescriptor();
      case 0:
        return new AppendOperation_BehaviorDescriptor();
      case 9:
        return new ExtensionDeclaration_BehaviorDescriptor();
      case 21:
        return new ReferenceAppendPart_BehaviorDescriptor();
      case 8:
        return new EncodingLiteral_BehaviorDescriptor();
      case 7:
        return new EncodingDeclaration_BehaviorDescriptor();
      case 10:
        return new FilenameFunction_BehaviorDescriptor();
      case 22:
        return new StubOperationDeclaration_BehaviorDescriptor();
      default:
        return BehaviorAspectInterpreted.getInstance().getDescriptor(fqName);
    }
  }
  private static String[] stringSwitchCases_846f5o_a0a0b = new String[]{"jetbrains.mps.lang.textGen.structure.AppendOperation", "jetbrains.mps.lang.textGen.structure.BufferParameter", "jetbrains.mps.lang.textGen.structure.CollectionAppendPart", "jetbrains.mps.lang.textGen.structure.ConceptTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.ConstantStringAppendPart", "jetbrains.mps.lang.textGen.structure.ContextParameter", "jetbrains.mps.lang.textGen.structure.DecreaseDepthOperation", "jetbrains.mps.lang.textGen.structure.EncodingDeclaration", "jetbrains.mps.lang.textGen.structure.EncodingLiteral", "jetbrains.mps.lang.textGen.structure.ExtensionDeclaration", "jetbrains.mps.lang.textGen.structure.FilenameFunction", "jetbrains.mps.lang.textGen.structure.FoundErrorOperation", "jetbrains.mps.lang.textGen.structure.GenerateTextDeclaration", "jetbrains.mps.lang.textGen.structure.IncreaseDepthOperation", "jetbrains.mps.lang.textGen.structure.IndentBufferOperation", "jetbrains.mps.lang.textGen.structure.LanguageTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.NewLineAppendPart", "jetbrains.mps.lang.textGen.structure.NodeAppendPart", "jetbrains.mps.lang.textGen.structure.NodeParameter", "jetbrains.mps.lang.textGen.structure.OperationCall", "jetbrains.mps.lang.textGen.structure.OperationDeclaration", "jetbrains.mps.lang.textGen.structure.ReferenceAppendPart", "jetbrains.mps.lang.textGen.structure.StubOperationDeclaration", "jetbrains.mps.lang.textGen.structure.UtilityMethodCall", "jetbrains.mps.lang.textGen.structure.UtilityMethodDeclaration", "jetbrains.mps.lang.textGen.structure.WithIndentOperation"};
}


File: languages/languageDesign/textGen/source_gen/jetbrains/mps/lang/textGen/editor/EditorAspectDescriptorImpl.java
package jetbrains.mps.lang.textGen.editor;

/*Generated by MPS */

import jetbrains.mps.openapi.editor.descriptor.EditorAspectDescriptor;
import java.util.Collection;
import jetbrains.mps.openapi.editor.descriptor.ConceptEditor;
import jetbrains.mps.smodel.runtime.ConceptDescriptor;
import java.util.Arrays;
import java.util.Collections;
import jetbrains.mps.openapi.editor.descriptor.ConceptEditorComponent;

public class EditorAspectDescriptorImpl implements EditorAspectDescriptor {

  public Collection<ConceptEditor> getEditors(ConceptDescriptor descriptor) {
    switch (Arrays.binarySearch(stringSwitchCases_xbvbvu_a0a0b, descriptor.getConceptFqName())) {
      case 0:
        return Collections.<ConceptEditor>singletonList(new AppendOperation_Editor());
      case 1:
        return Collections.<ConceptEditor>singletonList(new CollectionAppendPart_Editor());
      case 2:
        return Collections.<ConceptEditor>singletonList(new ConceptTextGenDeclaration_Editor());
      case 3:
        return Collections.<ConceptEditor>singletonList(new ConstantStringAppendPart_Editor());
      case 4:
        return Collections.<ConceptEditor>singletonList(new EncodingLiteral_Editor());
      case 5:
        return Collections.<ConceptEditor>singletonList(new FoundErrorOperation_Editor());
      case 6:
        return Collections.<ConceptEditor>singletonList(new LanguageTextGenDeclaration_Editor());
      case 7:
        return Collections.<ConceptEditor>singletonList(new NewLineAppendPart_Editor());
      case 8:
        return Collections.<ConceptEditor>singletonList(new NodeAppendPart_Editor());
      case 9:
        return Collections.<ConceptEditor>singletonList(new OperationCall_Editor());
      case 10:
        return Collections.<ConceptEditor>singletonList(new OperationDeclaration_Editor());
      case 11:
        return Collections.<ConceptEditor>singletonList(new ReferenceAppendPart_Editor());
      case 12:
        return Collections.<ConceptEditor>singletonList(new SimpleTextGenOperation_Editor());
      case 13:
        return Collections.<ConceptEditor>singletonList(new StubOperationDeclaration_Editor());
      case 14:
        return Collections.<ConceptEditor>singletonList(new UtilityMethodCall_Editor());
      case 15:
        return Collections.<ConceptEditor>singletonList(new UtilityMethodDeclaration_Editor());
      case 16:
        return Collections.<ConceptEditor>singletonList(new WithIndentOperation_Editor());
      default:
    }
    return Collections.<ConceptEditor>emptyList();
  }
  public Collection<ConceptEditorComponent> getEditorComponents(ConceptDescriptor descriptor, String editorComponentId) {
    return Collections.<ConceptEditorComponent>emptyList();
  }


  private static String[] stringSwitchCases_xbvbvu_a0a0b = new String[]{"jetbrains.mps.lang.textGen.structure.AppendOperation", "jetbrains.mps.lang.textGen.structure.CollectionAppendPart", "jetbrains.mps.lang.textGen.structure.ConceptTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.ConstantStringAppendPart", "jetbrains.mps.lang.textGen.structure.EncodingLiteral", "jetbrains.mps.lang.textGen.structure.FoundErrorOperation", "jetbrains.mps.lang.textGen.structure.LanguageTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.NewLineAppendPart", "jetbrains.mps.lang.textGen.structure.NodeAppendPart", "jetbrains.mps.lang.textGen.structure.OperationCall", "jetbrains.mps.lang.textGen.structure.OperationDeclaration", "jetbrains.mps.lang.textGen.structure.ReferenceAppendPart", "jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation", "jetbrains.mps.lang.textGen.structure.StubOperationDeclaration", "jetbrains.mps.lang.textGen.structure.UtilityMethodCall", "jetbrains.mps.lang.textGen.structure.UtilityMethodDeclaration", "jetbrains.mps.lang.textGen.structure.WithIndentOperation"};
}


File: languages/languageDesign/textGen/source_gen/jetbrains/mps/lang/textGen/structure/StructureAspectDescriptor.java
package jetbrains.mps.lang.textGen.structure;

/*Generated by MPS */

import jetbrains.mps.smodel.runtime.BaseStructureAspectDescriptor;
import jetbrains.mps.smodel.runtime.ConceptDescriptor;
import jetbrains.mps.smodel.runtime.impl.ConceptDescriptorBuilder;
import jetbrains.mps.smodel.adapter.ids.MetaIdFactory;
import jetbrains.mps.smodel.runtime.StaticScope;
import java.util.Collection;
import java.util.Arrays;
import org.jetbrains.annotations.Nullable;

public class StructureAspectDescriptor extends BaseStructureAspectDescriptor {

  /*package*/ final ConceptDescriptor myConceptAbstractAppendPart = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.AbstractAppendPart", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).super_("jetbrains.mps.lang.core.structure.BaseConcept").super_(MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL)).parents("jetbrains.mps.lang.core.structure.BaseConcept").parentIds(MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL)).abstract_().create();
  /*package*/ final ConceptDescriptor myConceptAbstractTextGenDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.AbstractTextGenDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f60f06a49L)).super_("jetbrains.mps.lang.core.structure.BaseConcept").super_(MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL)).parents("jetbrains.mps.lang.core.structure.BaseConcept", "jetbrains.mps.baseLanguage.structure.IValidIdentifier", "jetbrains.mps.lang.core.structure.InterfacePart").parentIds(MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL), MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x11a3afa8c0dL), MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x12509ddfaa98f128L)).abstract_().create();
  /*package*/ final ConceptDescriptor myConceptAbstractTextGenParameter = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).super_("jetbrains.mps.baseLanguage.structure.ConceptFunctionParameter").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x101c66e2c0bL)).parents("jetbrains.mps.baseLanguage.structure.ConceptFunctionParameter", "jetbrains.mps.lang.core.structure.IDontSubstituteByDefault").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x101c66e2c0bL), MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x19796fa16a19888bL)).abstract_().staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptAppendOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.AppendOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x120153077caL)).super_("jetbrains.mps.baseLanguage.structure.Statement").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).parents("jetbrains.mps.baseLanguage.structure.Statement").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).childDescriptors(new ConceptDescriptorBuilder.Link(1237306115446L, "part", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L), false, true, false)).children(new String[]{"part"}, new boolean[]{true}).alias("append", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptBufferParameter = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.BufferParameter", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f65197df2L)).super_("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).parents("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).alias("buffer", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptCollectionAppendPart = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.CollectionAppendPart", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201527819cL)).super_("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).parents("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).propertyDescriptors(new ConceptDescriptorBuilder.Prop(1237306003719L, "separator"), new ConceptDescriptorBuilder.Prop(1237983969951L, "withSeparator")).properties("separator", "withSeparator").childDescriptors(new ConceptDescriptorBuilder.Link(1237305945551L, "list", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL), false, false, false)).children(new String[]{"list"}, new boolean[]{false}).alias("$list{", "collection").create();
  /*package*/ final ConceptDescriptor myConceptConceptTextGenDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.ConceptTextGenDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f3c776369L)).super_("jetbrains.mps.lang.textGen.structure.AbstractTextGenDeclaration").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f60f06a49L)).parents("jetbrains.mps.lang.textGen.structure.AbstractTextGenDeclaration", "jetbrains.mps.lang.structure.structure.IConceptAspect").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f60f06a49L), MetaIdFactory.conceptId(0xc72da2b97cce4447L, 0x8389f407dc1158b7L, 0x24614259e94f0c84L)).referenceDescriptors(new ConceptDescriptorBuilder.Ref(1233670257997L, "conceptDeclaration", MetaIdFactory.conceptId(0xc72da2b97cce4447L, 0x8389f407dc1158b7L, 0x1103553c5ffL), false)).references("conceptDeclaration").childDescriptors(new ConceptDescriptorBuilder.Link(7991274449437422201L, "extension", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x7bf48616723f681dL), true, false, false), new ConceptDescriptorBuilder.Link(1224137887853744062L, "encoding", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x10fd02ec599e8fbbL), true, false, false), new ConceptDescriptorBuilder.Link(1233749296504L, "textGenBlock", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f412f8790L), false, false, false), new ConceptDescriptorBuilder.Link(45307784116711884L, "filename", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0xa0f73089d40b8eL), true, false, false)).children(new String[]{"extension", "encoding", "textGenBlock", "filename"}, new boolean[]{false, false, false, false}).create();
  /*package*/ final ConceptDescriptor myConceptConstantStringAppendPart = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.ConstantStringAppendPart", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x12015288286L)).super_("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).parents("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).propertyDescriptors(new ConceptDescriptorBuilder.Prop(1237305576108L, "value"), new ConceptDescriptorBuilder.Prop(1237306361677L, "withIndent")).properties("value", "withIndent").alias("constant", "constant string").create();
  /*package*/ final ConceptDescriptor myConceptContextParameter = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.ContextParameter", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f60cd534bL)).super_("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).parents("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).alias("context", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptDecreaseDepthOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.DecreaseDepthOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4165704bL)).super_("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).parents("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).alias("decrease depth", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptEncodingDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.EncodingDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x10fd02ec599e8f93L)).super_("jetbrains.mps.baseLanguage.structure.ConceptFunction").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).parents("jetbrains.mps.baseLanguage.structure.ConceptFunction", "jetbrains.mps.lang.textGen.structure.EncodingDeclarationBase").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L), MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x10fd02ec599e8fbbL)).alias("encoding", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptEncodingDeclarationBase = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.EncodingDeclarationBase", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x10fd02ec599e8fbbL)).interface_().create();
  /*package*/ final ConceptDescriptor myConceptEncodingLiteral = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.EncodingLiteral", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x63754d97e1c86b8cL)).super_("jetbrains.mps.lang.core.structure.BaseConcept").super_(MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL)).parents("jetbrains.mps.lang.core.structure.BaseConcept", "jetbrains.mps.lang.textGen.structure.EncodingDeclarationBase").parentIds(MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x10802efe25aL), MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x10fd02ec599e8fbbL)).propertyDescriptors(new ConceptDescriptorBuilder.Prop(7166719696753421197L, "encoding")).properties("encoding").alias("encoding literal", "").create();
  /*package*/ final ConceptDescriptor myConceptExtensionDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.ExtensionDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x7bf48616723f681dL)).super_("jetbrains.mps.baseLanguage.structure.ConceptFunction").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).parents("jetbrains.mps.baseLanguage.structure.ConceptFunction").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).alias("extension", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptFilenameFunction = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.FilenameFunction", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0xa0f73089d40b8eL)).super_("jetbrains.mps.baseLanguage.structure.ConceptFunction").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).parents("jetbrains.mps.baseLanguage.structure.ConceptFunction").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).final_().alias("filename", "name of output file").create();
  /*package*/ final ConceptDescriptor myConceptFoundErrorOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.FoundErrorOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f7f7ff1bdL)).super_("jetbrains.mps.baseLanguage.structure.Statement").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).parents("jetbrains.mps.baseLanguage.structure.Statement").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).childDescriptors(new ConceptDescriptorBuilder.Link(1237470722868L, "text", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL), true, false, false)).children(new String[]{"text"}, new boolean[]{false}).alias("found error", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptGenerateTextDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.GenerateTextDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f412f8790L)).super_("jetbrains.mps.baseLanguage.structure.ConceptFunction").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).parents("jetbrains.mps.baseLanguage.structure.ConceptFunction").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0x108bbca0f48L)).alias("do generate text", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptIncreaseDepthOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.IncreaseDepthOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f41648039L)).super_("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).parents("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).alias("increase depth", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptIndentBufferOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.IndentBufferOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b64a5c9L)).super_("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).parents("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).alias("indent buffer", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptLanguageTextGenDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.LanguageTextGenDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b71f51fL)).super_("jetbrains.mps.lang.textGen.structure.AbstractTextGenDeclaration").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f60f06a49L)).parents("jetbrains.mps.lang.textGen.structure.AbstractTextGenDeclaration").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f60f06a49L)).referenceDescriptors(new ConceptDescriptorBuilder.Ref(1234781160172L, "baseTextGen", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b71f51fL), true)).references("baseTextGen").childDescriptors(new ConceptDescriptorBuilder.Link(1233922432965L, "operation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b80e9d3L), true, true, false), new ConceptDescriptorBuilder.Link(1234526822589L, "function", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f6f6a18e4L), true, true, false)).children(new String[]{"operation", "function"}, new boolean[]{true, true}).create();
  /*package*/ final ConceptDescriptor myConceptNewLineAppendPart = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.NewLineAppendPart", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x12015232fd0L)).super_("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).parents("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).alias("\\n", "new line").create();
  /*package*/ final ConceptDescriptor myConceptNodeAppendPart = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.NodeAppendPart", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x12015251a28L)).super_("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).parents("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).propertyDescriptors(new ConceptDescriptorBuilder.Prop(1237306318654L, "withIndent")).properties("withIndent").childDescriptors(new ConceptDescriptorBuilder.Link(1237305790512L, "value", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL), false, false, false)).children(new String[]{"value"}, new boolean[]{false}).alias("${", "node or property").create();
  /*package*/ final ConceptDescriptor myConceptNodeParameter = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.NodeParameter", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f411d576bL)).super_("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).parents("jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f84e1988dL)).alias("node", "").staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptOperationCall = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.OperationCall", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4ba6faaaL)).super_("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).parents("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).referenceDescriptors(new ConceptDescriptorBuilder.Ref(1234190664409L, "function", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b80e9d3L), false)).references("function").childDescriptors(new ConceptDescriptorBuilder.Link(1234191323697L, "parameter", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL), true, true, false)).children(new String[]{"parameter"}, new boolean[]{true}).create();
  /*package*/ final ConceptDescriptor myConceptOperationDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.OperationDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b80e9d3L)).super_("jetbrains.mps.baseLanguage.structure.BaseMethodDeclaration").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b1fcL)).parents("jetbrains.mps.baseLanguage.structure.BaseMethodDeclaration", "jetbrains.mps.lang.core.structure.ImplementationWithStubPart").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b1fcL), MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x612410e32cf46136L)).propertyDescriptors(new ConceptDescriptorBuilder.Prop(1234264079341L, "operationName")).properties("operationName").alias("new operation", "").create();
  /*package*/ final ConceptDescriptor myConceptReferenceAppendPart = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.ReferenceAppendPart", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x5fec1f33fd3007f8L)).super_("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).parents("jetbrains.mps.lang.textGen.structure.AbstractAppendPart").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x1201521c456L)).propertyDescriptors(new ConceptDescriptorBuilder.Prop(4809320654438971908L, "uniqNameInFile")).properties("uniqNameInFile").childDescriptors(new ConceptDescriptorBuilder.Link(6911933836258445307L, "reference", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL), false, false, false)).children(new String[]{"reference"}, new boolean[]{false}).alias("$ref{", "reference").create();
  /*package*/ final ConceptDescriptor myConceptSimpleTextGenOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4153bc8cL)).super_("jetbrains.mps.baseLanguage.structure.Statement").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).parents("jetbrains.mps.baseLanguage.structure.Statement").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).abstract_().staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptStubOperationDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.StubOperationDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x2bacbf19e457bd3bL)).super_("jetbrains.mps.lang.textGen.structure.OperationDeclaration").super_(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b80e9d3L)).parents("jetbrains.mps.lang.textGen.structure.OperationDeclaration", "jetbrains.mps.lang.core.structure.IDontSubstituteByDefault", "jetbrains.mps.lang.core.structure.ISuppressErrors", "jetbrains.mps.lang.core.structure.IStubForAnotherConcept").parentIds(MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f4b80e9d3L), MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x19796fa16a19888bL), MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x2f16f1b357e19f43L), MetaIdFactory.conceptId(0xceab519525ea4f22L, 0x9b92103b95ca8c0cL, 0x226fb4c3ba26d45L)).create();
  /*package*/ final ConceptDescriptor myConceptUtilityMethodCall = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.UtilityMethodCall", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f6faa8c98L)).super_("jetbrains.mps.baseLanguage.structure.Expression").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL)).parents("jetbrains.mps.baseLanguage.structure.Expression").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL)).referenceDescriptors(new ConceptDescriptorBuilder.Ref(1234529163244L, "function", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f6f6a18e4L), false)).references("function").childDescriptors(new ConceptDescriptorBuilder.Link(1234529174917L, "parameter", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8c37f506fL), true, true, false)).children(new String[]{"parameter"}, new boolean[]{true}).staticScope(StaticScope.NONE).create();
  /*package*/ final ConceptDescriptor myConceptUtilityMethodDeclaration = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.UtilityMethodDeclaration", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11f6f6a18e4L)).super_("jetbrains.mps.baseLanguage.structure.BaseMethodDeclaration").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b1fcL)).parents("jetbrains.mps.baseLanguage.structure.BaseMethodDeclaration").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b1fcL)).alias("new private function", "").create();
  /*package*/ final ConceptDescriptor myConceptWithIndentOperation = new ConceptDescriptorBuilder("jetbrains.mps.lang.textGen.structure.WithIndentOperation", MetaIdFactory.conceptId(0xb83431fe5c8f40bcL, 0x8a3665e25f4dd253L, 0x11fd28e1146L)).super_("jetbrains.mps.baseLanguage.structure.Statement").super_(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).parents("jetbrains.mps.baseLanguage.structure.Statement").parentIds(MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b215L)).childDescriptors(new ConceptDescriptorBuilder.Link(1236188238861L, "list", MetaIdFactory.conceptId(0xf3061a5392264cc5L, 0xa443f952ceaf5816L, 0xf8cc56b200L), false, false, false)).children(new String[]{"list"}, new boolean[]{false}).alias("with indent {", "code block").staticScope(StaticScope.NONE).create();

  @Override
  public Collection<ConceptDescriptor> getDescriptors() {
    return Arrays.asList(myConceptAbstractAppendPart, myConceptAbstractTextGenDeclaration, myConceptAbstractTextGenParameter, myConceptAppendOperation, myConceptBufferParameter, myConceptCollectionAppendPart, myConceptConceptTextGenDeclaration, myConceptConstantStringAppendPart, myConceptContextParameter, myConceptDecreaseDepthOperation, myConceptEncodingDeclaration, myConceptEncodingDeclarationBase, myConceptEncodingLiteral, myConceptExtensionDeclaration, myConceptFilenameFunction, myConceptFoundErrorOperation, myConceptGenerateTextDeclaration, myConceptIncreaseDepthOperation, myConceptIndentBufferOperation, myConceptLanguageTextGenDeclaration, myConceptNewLineAppendPart, myConceptNodeAppendPart, myConceptNodeParameter, myConceptOperationCall, myConceptOperationDeclaration, myConceptReferenceAppendPart, myConceptSimpleTextGenOperation, myConceptStubOperationDeclaration, myConceptUtilityMethodCall, myConceptUtilityMethodDeclaration, myConceptWithIndentOperation);
  }

  @Override
  @Nullable
  public ConceptDescriptor getDescriptor(String conceptFqName) {
    switch (Arrays.binarySearch(stringSwitchCases_1htk8d_a0a0jb, conceptFqName)) {
      case 0:
        return myConceptAbstractAppendPart;
      case 1:
        return myConceptAbstractTextGenDeclaration;
      case 2:
        return myConceptAbstractTextGenParameter;
      case 3:
        return myConceptAppendOperation;
      case 4:
        return myConceptBufferParameter;
      case 5:
        return myConceptCollectionAppendPart;
      case 6:
        return myConceptConceptTextGenDeclaration;
      case 7:
        return myConceptConstantStringAppendPart;
      case 8:
        return myConceptContextParameter;
      case 9:
        return myConceptDecreaseDepthOperation;
      case 10:
        return myConceptEncodingDeclaration;
      case 11:
        return myConceptEncodingDeclarationBase;
      case 12:
        return myConceptEncodingLiteral;
      case 13:
        return myConceptExtensionDeclaration;
      case 14:
        return myConceptFilenameFunction;
      case 15:
        return myConceptFoundErrorOperation;
      case 16:
        return myConceptGenerateTextDeclaration;
      case 17:
        return myConceptIncreaseDepthOperation;
      case 18:
        return myConceptIndentBufferOperation;
      case 19:
        return myConceptLanguageTextGenDeclaration;
      case 20:
        return myConceptNewLineAppendPart;
      case 21:
        return myConceptNodeAppendPart;
      case 22:
        return myConceptNodeParameter;
      case 23:
        return myConceptOperationCall;
      case 24:
        return myConceptOperationDeclaration;
      case 25:
        return myConceptReferenceAppendPart;
      case 26:
        return myConceptSimpleTextGenOperation;
      case 27:
        return myConceptStubOperationDeclaration;
      case 28:
        return myConceptUtilityMethodCall;
      case 29:
        return myConceptUtilityMethodDeclaration;
      case 30:
        return myConceptWithIndentOperation;
      default:
        return null;
    }
  }
  private static String[] stringSwitchCases_1htk8d_a0a0jb = new String[]{"jetbrains.mps.lang.textGen.structure.AbstractAppendPart", "jetbrains.mps.lang.textGen.structure.AbstractTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.AbstractTextGenParameter", "jetbrains.mps.lang.textGen.structure.AppendOperation", "jetbrains.mps.lang.textGen.structure.BufferParameter", "jetbrains.mps.lang.textGen.structure.CollectionAppendPart", "jetbrains.mps.lang.textGen.structure.ConceptTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.ConstantStringAppendPart", "jetbrains.mps.lang.textGen.structure.ContextParameter", "jetbrains.mps.lang.textGen.structure.DecreaseDepthOperation", "jetbrains.mps.lang.textGen.structure.EncodingDeclaration", "jetbrains.mps.lang.textGen.structure.EncodingDeclarationBase", "jetbrains.mps.lang.textGen.structure.EncodingLiteral", "jetbrains.mps.lang.textGen.structure.ExtensionDeclaration", "jetbrains.mps.lang.textGen.structure.FilenameFunction", "jetbrains.mps.lang.textGen.structure.FoundErrorOperation", "jetbrains.mps.lang.textGen.structure.GenerateTextDeclaration", "jetbrains.mps.lang.textGen.structure.IncreaseDepthOperation", "jetbrains.mps.lang.textGen.structure.IndentBufferOperation", "jetbrains.mps.lang.textGen.structure.LanguageTextGenDeclaration", "jetbrains.mps.lang.textGen.structure.NewLineAppendPart", "jetbrains.mps.lang.textGen.structure.NodeAppendPart", "jetbrains.mps.lang.textGen.structure.NodeParameter", "jetbrains.mps.lang.textGen.structure.OperationCall", "jetbrains.mps.lang.textGen.structure.OperationDeclaration", "jetbrains.mps.lang.textGen.structure.ReferenceAppendPart", "jetbrains.mps.lang.textGen.structure.SimpleTextGenOperation", "jetbrains.mps.lang.textGen.structure.StubOperationDeclaration", "jetbrains.mps.lang.textGen.structure.UtilityMethodCall", "jetbrains.mps.lang.textGen.structure.UtilityMethodDeclaration", "jetbrains.mps.lang.textGen.structure.WithIndentOperation"};
}
