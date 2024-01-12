Refactoring Types: ['Extract Method']
/jitwatch/core/JITWatchConstants.java
/*
 * Copyright (c) 2013, 2014 Chris Newland.
 * Licensed under https://github.com/AdoptOpenJDK/jitwatch/blob/master/LICENSE-BSD
 * Instructions: https://github.com/AdoptOpenJDK/jitwatch/wiki
 */
package org.adoptopenjdk.jitwatch.core;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.regex.Pattern;

public final class JITWatchConstants
{
	private JITWatchConstants()
	{
	}

	// Enable debugging for specific functionality
	// DEBUG level logging requires editing src/main/resources/logback.xml
	public static final boolean DEBUG_LOGGING = false;
	public static final boolean DEBUG_LOGGING_BYTECODE = false;
	public static final boolean DEBUG_LOGGING_CLASSPATH = false;
	public static final boolean DEBUG_LOGGING_ASSEMBLY = false;
	public static final boolean DEBUG_LOGGING_SIG_MATCH = false;
	public static final boolean DEBUG_LOGGING_OVC = false;
	public static final boolean DEBUG_LOGGING_PARSE_DICTIONARY = false;
	public static final boolean DEBUG_LOGGING_TRIVIEW = false;
	public static final boolean DEBUG_LOGGING_TAGPROCESSOR = false;

	public static final boolean DEBUG_MEMBER_CREATION = false;

	public static final int DEFAULT_FREQ_INLINE_SIZE = 35;
	public static final int DEFAULT_MAX_INLINE_SIZE = 325;
	public static final int DEFAULT_COMPILER_THRESHOLD = 10000;

	public static final String TAG_XML = "<?xml";
	public static final String TAG_TTY = "<tty>";
	public static final String TAG_TTY_CLOSE = "</tty>";
	public static final String TAG_COMPILATION_LOG = "<compilation_log";
	public static final String TAG_COMPILATION_LOG_CLOSE = "</compilation_log>";
	public static final String TAG_HOTSPOT_LOG = "<hotspot_log ";
	public static final String TAG_HOTSPOT_LOG_CLOSE = "</hotspot_log>";

	public static final String S_FRAGMENT = "fragment";
	public static final String TAG_OPEN_FRAGMENT = "<fragment>";
	public static final String TAG_CLOSE_FRAGMENT = "</fragment>";
	public static final String TAG_OPEN_CDATA = "<![CDATA[";
	public static final String TAG_CLOSE_CDATA = "]]>";
	public static final String TAG_OPEN_CLOSE_CDATA = TAG_CLOSE_CDATA + TAG_OPEN_CDATA;

	public static final Set<String> SKIP_HEADER_TAGS = new HashSet<>(Arrays.asList(new String[] { TAG_XML, TAG_HOTSPOT_LOG }));

	public static final Set<String> SKIP_BODY_TAGS = new HashSet<>(Arrays.asList(new String[] { TAG_TTY_CLOSE, TAG_COMPILATION_LOG,
			TAG_COMPILATION_LOG_CLOSE, TAG_HOTSPOT_LOG_CLOSE }));

	public static final String NATIVE_CODE_START = "Decoding compiled method";
	public static final String NATIVE_CODE_METHOD_MARK = "# {method}";
	public static final String LOADED = "[Loaded ";
	public static final String METHOD = "method";
	public static final String S_PARSE = "parse";
	public static final String S_TYPE = "type";

	public static final String S_CODE_COLON = "Code:";

	public static final String DEFAULT_PACKAGE_NAME = "(default package)";
	public static final String TREE_PACKAGE_ROOT = "Packages";

	public static final String TAG_VM_VERSION = "vm_version";
	public static final String TAG_RELEASE = "release";
	public static final String TAG_TWEAK_VM = "TweakVM";

	public static final String TAG_TASK_QUEUED = "task_queued";
	public static final String TAG_NMETHOD = "nmethod";
	public static final String TAG_TASK = "task";
	public static final String TAG_BC = "bc";
	public static final String TAG_CALL = "call";
	public static final String TAG_CODE_CACHE = "code_cache";
	public static final String TAG_TASK_DONE = "task_done";
	public static final String TAG_START_COMPILE_THREAD = "start_compile_thread";
	public static final String TAG_PARSE = S_PARSE;
	public static final String TAG_PHASE = "phase";
	public static final String TAG_KLASS = "klass";
	public static final String TAG_TYPE = S_TYPE;
	public static final String TAG_METHOD = METHOD;
	public static final String TAG_INTRINSIC = "intrinsic";
	public static final String TAG_INLINE_FAIL = "inline_fail";
	public static final String TAG_INLINE_SUCCESS = "inline_success";
	public static final String TAG_BRANCH = "branch";
	public static final String TAG_WRITER = "writer";
	public static final String TAG_VM_ARGUMENTS = "vm_arguments";
	public static final String TAG_ELIMINATE_ALLOCATION = "eliminate_allocation";
	public static final String TAG_JVMS = "jvms";

	public static final String TAG_COMMAND = "command";

	public static final String OSR = "osr";
	public static final String C2N = "c2n";
	public static final String C1 = "C1";
	public static final String C2 = "C2";

	public static final String ATTR_METHOD = METHOD;
	public static final String ATTR_COMPILE_ID = "compile_id";
	public static final String ATTR_COMPILE_KIND = "compile_kind";
	public static final String ATTR_STAMP = "stamp";
	public static final String ATTR_NAME = "name";
	public static final String ATTR_BCI = "bci";
	public static final String ATTR_CODE = "code";
	public static final String ATTR_COMPILER = "compiler";
	public static final String ATTR_FREE_CODE_CACHE = "free_code_cache";
	public static final String ATTR_NMSIZE = "nmsize";
	public static final String ATTR_BYTES = "bytes";
	public static final String ATTR_IICOUNT = "iicount";
	public static final String ATTR_COMPILE_MILLIS = "compileMillis";
	public static final String ATTR_DECOMPILES = "decompiles";
	public static final String ATTR_PARSE = S_PARSE;
	public static final String ATTR_TYPE = S_TYPE;
	public static final String ATTR_BUILDIR = "buildIR";
	public static final String ATTR_ID = "id";
	public static final String ATTR_HOLDER = "holder";
	public static final String ATTR_RETURN = "return";
	public static final String ATTR_REASON = "reason";
	public static final String ATTR_ARGUMENTS = "arguments";
	public static final String ATTR_BRANCH_COUNT = "cnt";
	public static final String ATTR_BRANCH_TAKEN = "taken";
	public static final String ATTR_BRANCH_NOT_TAKEN = "not_taken";
	public static final String ATTR_BRANCH_PROB = "prob";
	public static final String ATTR_COUNT = "count";
	public static final String ATTR_PROF_FACTOR = "prof_factor";

	public static final String ALWAYS = "always";
	public static final String NEVER = "never";

	public static final String S_ENTITY_APOS = "&apos;";
	public static final String S_ENTITY_LT = "&lt;";
	public static final String S_ENTITY_GT = "&gt;";

	public static final String S_PACKAGE = "package";
	public static final String S_CLASS = "class";

	public static final String S_PROFILE_DEFAULT = "Default";
	public static final String S_PROFILE_SANDBOX = "Sandbox";

	public static final String S_CLASS_PREFIX_INVOKE = "java.lang.invoke.";
	public static final String S_CLASS_PREFIX_STREAM_COLLECTORS = "java.util.stream.Collectors$";
	public static final String S_CLASS_PREFIX_SUN_REFLECT_GENERATED = "sun.reflect.Generated";

	public static final String HEXA_POSTFIX = "h";

	private static final Set<String> SET_AUTOGENERATED_PREFIXES = new HashSet<>();

	static
	{
		SET_AUTOGENERATED_PREFIXES.add(S_CLASS_PREFIX_INVOKE);
		SET_AUTOGENERATED_PREFIXES.add(S_CLASS_PREFIX_STREAM_COLLECTORS);
		SET_AUTOGENERATED_PREFIXES.add(S_CLASS_PREFIX_SUN_REFLECT_GENERATED);
	}

	public static final Set<String> getAutoGeneratedClassPrefixes()
	{
		return Collections.unmodifiableSet(SET_AUTOGENERATED_PREFIXES);
	}
	
	public static final String S_CLASS_AUTOGENERATED_LAMBDA = "$$Lambda";

	public static final String REGEX_GROUP_ANY = "(.*)";
	public static final String REGEX_ZERO_OR_MORE_SPACES = "( )*";
	public static final String REGEX_ONE_OR_MORE_SPACES = "( )+";
	public static final String REGEX_UNICODE_PARAM_NAME = "([0-9\\p{L}_]+)";
	public static final String REGEX_UNICODE_PACKAGE_NAME = "([0-9\\p{L}_\\.]*)";

	public static final String S_OPEN_PARENTHESES = "(";
	public static final String S_CLOSE_PARENTHESES = ")";
	public static final String S_ESCAPED_OPEN_PARENTHESES = "\\(";
	public static final String S_ESCAPED_CLOSE_PARENTHESES = "\\)";
	public static final String S_OPEN_ANGLE = "<";
	public static final String S_CLOSE_ANGLE = ">";
	public static final String S_OPEN_SQUARE = "[";
	public static final String S_CLOSE_SQUARE = "]";
	public static final String S_ARRAY_BRACKET_PAIR = "[]";
	public static final String S_ESCAPED_OPEN_SQUARE = "\\[";
	public static final String S_ESCAPED_CLOSE_SQUARE = "\\]";
	public static final String S_ESCAPED_DOT = "\\.";
	public static final String S_OPEN_BRACE = "{";
	public static final String S_CLOSE_BRACE = "}";
	public static final String S_AT = "@";
	public static final String S_PERCENT = "%";
	public static final String S_DOLLAR = "$";
	public static final String S_HASH = "#";
	public static final String S_SPACE = " ";
	public static final String S_NEWLINE = "\n";
	public static final String S_NEWLINE_CR = "\r";
	public static final String S_TAB = "\t";
	public static final String S_DOUBLE_SPACE = "  ";
	public static final String S_EMPTY = "";
	public static final String S_COLON = ":";
	public static final String S_SEMICOLON = ";";
	public static final String S_VARARGS_DOTS = "...";
	public static final String S_OBJECT_ARRAY_DEF = "[L";
	public static final String S_DOT = ".";
	public static final String S_ASTERISK = "*";
	public static final String S_COMMA = ",";
	public static final String S_SLASH = "/";
	public static final String S_DOUBLE_SLASH = "//";
	public static final String S_QUOTE = "'";
	public static final String S_DOUBLE_QUOTE = "\"";
	public static final String S_REGEX_WHITESPACE = "\\s+";
	public static final String S_BACKSLASH = "\\";
	public static final String S_XML_COMMENT_START = "<!--";
	public static final String S_XML_COMMENT_END = "-->";
	public static final String S_XML_DOC_START = "<?xml";
	public static final String S_XML_DOCTYPE_START = "<!DOCTYPE";
	public static final String S_BYTECODE_METHOD_COMMENT = "// Method";
	public static final String S_BYTECODE_INTERFACEMETHOD_COMMENT = "// InterfaceMethod";
	public static final String S_DEFAULT = "default";
	public static final String S_FILE_COLON = "file:";
	public static final String S_DOT_CLASS = ".class";
	public static final String S_GENERICS_WILDCARD = "<?>";
	public static final String S_OPTIMIZER = "optimizer";
	
	public static final String S_TYPE_NAME_SHORT = "short";
	public static final String S_TYPE_NAME_CHARACTER = "char";
	public static final String S_TYPE_NAME_BYTE = "byte";
	public static final String S_TYPE_NAME_LONG = "long";
	public static final String S_TYPE_NAME_DOUBLE = "double";
	public static final String S_TYPE_NAME_BOOLEAN = "boolean";
	public static final String S_TYPE_NAME_INTEGER = "int";
	public static final String S_TYPE_NAME_FLOAT = "float";
	public static final String S_TYPE_NAME_VOID = "void";

	public static final String S_OPTIMIZED_VIRTUAL_CALL = "{optimized virtual_call}";

	public static final char C_SLASH = '/';
	public static final char C_OPEN_ANGLE = '<';
	public static final char C_CLOSE_ANGLE = '>';
	public static final char C_OPEN_PARENTHESES = '(';
	public static final char C_CLOSE_PARENTHESES = ')';
	public static final char C_OPEN_BRACE = '{';
	public static final char C_CLOSE_BRACE = '}';
	public static final char C_SPACE = ' ';
	public static final char C_HASH = '#';
	public static final char C_COMMA = ',';
	public static final char C_AT = '@';
	public static final char C_COLON = ':';
	public static final char C_EQUALS = '=';
	public static final char C_QUOTE = '\'';
	public static final char C_DOUBLE_QUOTE = '"';
	public static final char C_NEWLINE = '\n';
	public static final char C_DOT = '.';
	public static final char C_OBJECT_REF = 'L';
	public static final char C_SEMICOLON = ';';
	public static final char C_OPEN_SQUARE_BRACKET = '[';
	public static final char C_QUESTION = '?';
	public static final char C_BACKSLASH = '\\';
	public static final char C_HAT = '^';
	public static final char C_DOLLAR = '$';

	public static final String S_ASSEMBLY_ADDRESS = "0x";

	public static final String S_BYTECODE_MINOR_VERSION = "minor version:";
	public static final String S_BYTECODE_MAJOR_VERSION = "major version:";
	public static final String S_BYTECODE_SIGNATURE = "Signature:";
	public static final String S_BYTECODE_SOURCE_FILE= "SourceFile:";

	public static final String S_POLYMORPHIC_SIGNATURE = "PolymorphicSignature";

	public static final String S_BYTECODE_CONSTANT_POOL = "Constant pool:";
	public static final String S_BYTECODE_CODE = "Code:";
	public static final String S_BYTECODE_EXCEPTIONS = "Exceptions:";
	public static final String S_BYTECODE_RUNTIMEVISIBLEANNOTATIONS = "RuntimeVisibleAnnotations:";
	public static final String S_BYTECODE_LINENUMBERTABLE = "LineNumberTable:";
	public static final String S_BYTECODE_LOCALVARIABLETABLE = "LocalVariableTable:";
	public static final String S_BYTECODE_STACKMAPTABLE = "StackMapTable:";
	public static final String S_BYTECODE_INNERCLASSES = "InnerClasses:";

	public static final String S_CONSTRUCTOR_INIT = "<init>";
	public static final String S_STATIC_INIT = "<clinit>";
	public static final String S_BYTECODE_STATIC_INITIALISER_SIGNATURE = "static {}";

	public static final String PUBLIC = "public";
	public static final String PRIVATE = "private";
	public static final String PROTECTED = "protected";
	public static final String STATIC = "static";
	public static final String FINAL = "final";
	public static final String SYNCHRONIZED = "synchronized";
	public static final String STRICTFP = "strictfp";
	public static final String NATIVE = "native";
	public static final String ABSTRACT = "abstract";

	public static final String[] MODIFIERS = new String[] { PUBLIC, PRIVATE, PROTECTED, STATIC, FINAL, SYNCHRONIZED, STRICTFP,
		NATIVE, ABSTRACT };

	public static final Pattern PATTERN_LOG_SIGNATURE = Pattern
			.compile("^([0-9]+):\\s([0-9a-z_]+)\\s?([#0-9a-z,\\- ]+)?\\s?\\{?\\s?(//.*)?");

	public static final String VM_LANGUAGE_JAVA = "Java";
	public static final String VM_LANGUAGE_SCALA = "Scala";
	public static final String VM_LANGUAGE_JRUBY = "JRuby";
	public static final String VM_LANGUAGE_GROOVY = "Groovy";
	public static final String VM_LANGUAGE_KOTLIN = "Kotlin";
	public static final String VM_LANGUAGE_JAVASCRIPT = "JavaScript";
	public static final String VM_LANGUAGE_CLOJURE = "Clojure";

}

File: src/main/java/org/adoptopenjdk/jitwatch/journal/JournalUtil.java
/*
 * Copyright (c) 2013, 2014 Chris Newland.
 * Licensed under https://github.com/AdoptOpenJDK/jitwatch/blob/master/LICENSE-BSD
 * Instructions: https://github.com/AdoptOpenJDK/jitwatch/wiki
 */
package org.adoptopenjdk.jitwatch.journal;

import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_BUILDIR;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_COMPILE_KIND;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_HOLDER;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_METHOD;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_NAME;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_PARSE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C2N;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_DOT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_SLASH;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.DEBUG_LOGGING;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CLOSE_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CONSTRUCTOR_INIT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_ENTITY_GT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_ENTITY_LT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_OPEN_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_OPTIMIZER;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_ELIMINATE_ALLOCATION;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_NMETHOD;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_PARSE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_PHASE;

import java.util.List;

import org.adoptopenjdk.jitwatch.model.CompilerName;
import org.adoptopenjdk.jitwatch.model.IMetaMember;
import org.adoptopenjdk.jitwatch.model.IParseDictionary;
import org.adoptopenjdk.jitwatch.model.Journal;
import org.adoptopenjdk.jitwatch.model.LogParseException;
import org.adoptopenjdk.jitwatch.model.Tag;
import org.adoptopenjdk.jitwatch.model.Task;
import org.adoptopenjdk.jitwatch.util.ParseUtil;
import org.adoptopenjdk.jitwatch.util.StringUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class JournalUtil
{
	private static final Logger logger = LoggerFactory.getLogger(JournalUtil.class);

	private JournalUtil()
	{
	}

	public static void visitParseTagsOfLastTask(IMetaMember member, IJournalVisitable visitable) throws LogParseException
	{
		if (member == null)
		{
			throw new LogParseException("Cannot get Journal for null IMetaMember");
		}

		Journal journal = member.getJournal();

		Task lastTask = getLastTask(journal);

		if (lastTask == null)
		{
			if (!isJournalForCompile2NativeMember(journal))
			{
				logger.warn("No Task found in Journal for member {}", member);

				if (journal != null && journal.getEntryList().size() > 0)
				{
					logger.warn(journal.toString());
				}
			}
		}
		else
		{
			IParseDictionary parseDictionary = lastTask.getParseDictionary();

			Tag parsePhase = getParsePhase(lastTask);

			if (parsePhase != null)
			{
				List<Tag> parseTags = parsePhase.getNamedChildren(TAG_PARSE);

				if (DEBUG_LOGGING)
				{
					logger.debug("About to visit {} parse tags in last <task> of Journal", parseTags.size());
				}

				for (Tag parseTag : parseTags)
				{
					visitable.visitTag(parseTag, parseDictionary);
				}
			}
		}
	}

	public static void visitOptimizerTagsOfLastTask(IMetaMember member, IJournalVisitable visitable) throws LogParseException
	{
		if (member == null)
		{
			throw new LogParseException("Cannot get Journal for null IMetaMember");
		}

		Journal journal = member.getJournal();

		Task lastTask = getLastTask(journal);

		if (lastTask == null)
		{
			if (!isJournalForCompile2NativeMember(journal))
			{
				logger.warn("No Task found in Journal for member {}", member);

				if (journal != null && journal.getEntryList().size() > 0)
				{
					logger.warn(journal.toString());
				}
			}
		}
		else
		{
			IParseDictionary parseDictionary = lastTask.getParseDictionary();

			Tag optimizerPhase = getOptimizerPhase(lastTask);
			
			if (optimizerPhase != null)
			{
				List<Tag> eliminateAllocationTags = optimizerPhase.getNamedChildren(TAG_ELIMINATE_ALLOCATION);

				for (Tag eliminationTag : eliminateAllocationTags)
				{
					visitable.visitTag(eliminationTag, parseDictionary);
				}
			}
		}
	}

	
	public static boolean isJournalForCompile2NativeMember(Journal journal)
	{
		boolean result = false;

		if (journal != null)
		{
			List<Tag> entryList = journal.getEntryList();

			if (entryList.size() >= 1)
			{
				Tag tag = entryList.get(0);

				String tagName = tag.getName();

				if (TAG_NMETHOD.equals(tagName))
				{
					if (C2N.equals(tag.getAttribute(ATTR_COMPILE_KIND)))
					{
						result = true;
					}
				}
			}
		}

		return result;
	}

	public static boolean memberMatchesParseTag(IMetaMember member, Tag parseTag, IParseDictionary parseDictionary)
	{
		boolean result = false;

		if (DEBUG_LOGGING)
		{
			logger.debug("memberMatchesParseTag: {}", parseTag.toString(false));
		}

		String methodID = parseTag.getAttribute(ATTR_METHOD);

		Tag methodTag = parseDictionary.getMethod(methodID);

		if (DEBUG_LOGGING)
		{
			logger.debug("methodTag: {}", methodTag.toString(true));
		}

		if (methodTag != null)
		{
			String klassID = methodTag.getAttribute(ATTR_HOLDER);

			Tag klassTag = parseDictionary.getKlass(klassID);

			if (klassTag != null)
			{
				if (DEBUG_LOGGING)
				{
					logger.debug("klass tag: {}", klassTag.toString(false));
				}

				String klassAttrName = klassTag.getAttribute(ATTR_NAME);
				String methodAttrName = methodTag.getAttribute(ATTR_NAME).replace(S_ENTITY_LT, S_OPEN_ANGLE).replace(S_ENTITY_GT, S_CLOSE_ANGLE);		
				
				if (klassAttrName != null)
				{
					klassAttrName = klassAttrName.replace(C_SLASH, C_DOT);
				}

				String returnType = ParseUtil.getMethodTagReturn(methodTag, parseDictionary);
				List<String> paramTypes = ParseUtil.getMethodTagArguments(methodTag, parseDictionary);

				if (DEBUG_LOGGING)
				{
					logger.debug("memberName: {}/{}", member.getMemberName(), methodAttrName);
					logger.debug("metaClass : {}/{}", member.getMetaClass().getFullyQualifiedName(), klassAttrName);
					logger.debug("return    : {}/{}", member.getReturnTypeName(), returnType);
					logger.debug("params    : {}/{}", StringUtil.arrayToString(member.getParamTypeNames()),
							StringUtil.listToString(paramTypes));
				}

				boolean nameMatches;
							
				if (S_CONSTRUCTOR_INIT.equals(methodAttrName))
				{
					nameMatches = member.getMemberName().equals(klassAttrName);
				}
				else
				{
					nameMatches = member.getMemberName().equals(methodAttrName);
				}
				
				boolean klassMatches = member.getMetaClass().getFullyQualifiedName().equals(klassAttrName);
				boolean returnMatches = member.getReturnTypeName().equals(returnType);

				boolean paramsMatch = true;

				if (member.getParamTypeNames().length == paramTypes.size())
				{
					for (int pos = 0; pos < member.getParamTypeNames().length; pos++)
					{
						String memberParamType = member.getParamTypeNames()[pos];
						String tagParamType = paramTypes.get(pos);

						// logger.debug("checking: {}/{}", memberParamType,
						// tagParamType);

						if (!memberParamType.equals(tagParamType))
						{
							paramsMatch = false;
							break;
						}
					}
				}
				else
				{
					paramsMatch = false;
				}

				result = nameMatches && klassMatches && returnMatches && paramsMatch;

				if (DEBUG_LOGGING)
				{
					logger.debug("Matched name: {} klass: {} return: {} params: {}", nameMatches, klassMatches, returnMatches,
							paramsMatch);

					logger.debug("Matches member:{} = {}", member, result);
				}
			}
		}

		return result;
	}

	public static Task getLastTask(Journal journal)
	{
		Task lastTask = null;

		if (journal != null)
		{
			for (Tag tag : journal.getEntryList())
			{
				if (tag instanceof Task)
				{
					lastTask = (Task) tag;
				}
			}
		}

		return lastTask;
	}

	public static CompilerName getCompilerNameForLastTask(Journal journal)
	{
		Task lastTask = getLastTask(journal);

		CompilerName compilerName = null;

		if (lastTask != null)
		{
			compilerName = lastTask.getCompiler();
		}

		return compilerName;
	}

	private static Tag getParsePhase(Task lastTask)
	{
		Tag parsePhase = null;

		if (lastTask != null)
		{
			CompilerName compilerName = lastTask.getCompiler();

			String parseAttributeName = ATTR_PARSE;

			if (compilerName == CompilerName.C1)
			{
				parseAttributeName = ATTR_BUILDIR;
			}

			List<Tag> parsePhases = lastTask.getNamedChildrenWithAttribute(TAG_PHASE, ATTR_NAME, parseAttributeName);

			int count = parsePhases.size();

			if (count != 1)
			{
				logger.warn("Unexpected parse phase count: {}", count);
			}
			else
			{
				parsePhase = parsePhases.get(0);
			}
		}

		return parsePhase;
	}
	
	private static Tag getOptimizerPhase(Task lastTask)
	{
		Tag optimizerPhase = null;

		if (lastTask != null)
		{
			CompilerName compilerName = lastTask.getCompiler();

			List<Tag> parsePhases = lastTask.getNamedChildrenWithAttribute(TAG_PHASE, ATTR_NAME, S_OPTIMIZER);

			int count = parsePhases.size();

			if (count != 1)
			{
				logger.warn("Unexpected optimizer phase count: {}", count);
			}
			else
			{
				optimizerPhase = parsePhases.get(0);
			}
		}

		return optimizerPhase;
	}
}

File: src/main/java/org/adoptopenjdk/jitwatch/model/bytecode/BytecodeAnnotationBuilder.java
/*
 * Copyright (c) 2013, 2014 Chris Newland.
 * Licensed under https://github.com/AdoptOpenJDK/jitwatch/blob/master/LICENSE-BSD
 * Instructions: https://github.com/AdoptOpenJDK/jitwatch/wiki
 */
package org.adoptopenjdk.jitwatch.model.bytecode;

import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_BCI;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_BRANCH_COUNT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_BRANCH_NOT_TAKEN;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_BRANCH_PROB;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_BRANCH_TAKEN;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_CODE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_ID;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_NAME;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_REASON;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_TYPE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_NEWLINE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.DEBUG_LOGGING;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.DEBUG_LOGGING_BYTECODE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_BC;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_BRANCH;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_CALL;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_ELIMINATE_ALLOCATION;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_INLINE_FAIL;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_INLINE_SUCCESS;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_INTRINSIC;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_JVMS;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_METHOD;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_PARSE;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javafx.scene.paint.Color;

import org.adoptopenjdk.jitwatch.journal.IJournalVisitable;
import org.adoptopenjdk.jitwatch.journal.JournalUtil;
import org.adoptopenjdk.jitwatch.model.AnnotationException;
import org.adoptopenjdk.jitwatch.model.CompilerName;
import org.adoptopenjdk.jitwatch.model.IMetaMember;
import org.adoptopenjdk.jitwatch.model.IParseDictionary;
import org.adoptopenjdk.jitwatch.model.LineAnnotation;
import org.adoptopenjdk.jitwatch.model.LogParseException;
import org.adoptopenjdk.jitwatch.model.Tag;
import org.adoptopenjdk.jitwatch.util.InlineUtil;
import org.adoptopenjdk.jitwatch.util.ParseUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BytecodeAnnotationBuilder implements IJournalVisitable
{
	private static final Logger logger = LoggerFactory.getLogger(BytecodeAnnotationBuilder.class);

	private IMetaMember member;

	private List<BytecodeInstruction> instructions;

	private Map<Integer, LineAnnotation> result = new HashMap<>();

	public Map<Integer, LineAnnotation> buildBytecodeAnnotations(final IMetaMember member,
			final List<BytecodeInstruction> instructions) throws AnnotationException
	{
		this.member = member;
		this.instructions = instructions;
		result.clear();

		if (!member.isCompiled())
		{
			return result;
		}

		try
		{
			JournalUtil.visitParseTagsOfLastTask(member, this);

			JournalUtil.visitOptimizerTagsOfLastTask(member, this);

		}
		catch (LogParseException e)
		{
			logger.error("Error building bytecode annotations", e);

			Throwable cause = e.getCause();

			if (cause instanceof AnnotationException)
			{
				throw (AnnotationException) cause;
			}
		}

		return result;
	}

	@Override
	public void visitTag(Tag tag, IParseDictionary parseDictionary) throws LogParseException
	{
		switch (tag.getName())
		{
		case TAG_PARSE:
			if (JournalUtil.memberMatchesParseTag(member, tag, parseDictionary))
			{
				try
				{
					final CompilerName compilerName = JournalUtil.getCompilerNameForLastTask(member.getJournal());

					buildParseTagAnnotations(tag, result, instructions, compilerName);
				}
				catch (Exception e)
				{
					throw new LogParseException("Could not parse annotations", e);
				}
			}

			break;

		// <eliminate_allocation type='817'>
		// <jvms bci='44' method='818'/>
		// </eliminate_allocation>

		case TAG_ELIMINATE_ALLOCATION:

			List<Tag> childrenJVMS = tag.getNamedChildren(TAG_JVMS);

			for (Tag tagJVMS : childrenJVMS)
			{
				String bci = tagJVMS.getAttribute(ATTR_BCI);

				if (bci != null)
				{
					try
					{
						int bciValue = Integer.parseInt(bci);

						BytecodeInstruction instr = getInstructionAtIndex(instructions, bciValue);

						if (instr != null)
						{
							StringBuilder builder = new StringBuilder();
							builder.append("Object does not escape method.\n");
							builder.append("Heap allocation has been eliminated.\n");

							String typeID = tag.getAttribute(ATTR_TYPE);

							if (typeID != null)
							{
								String typeOrKlassName = ParseUtil.lookupType(typeID, parseDictionary);

								if (typeOrKlassName != null)
								{
									builder.append("Eliminated allocation was of type ").append(typeOrKlassName);
								}
							}

							storeAnnotation(bciValue, new LineAnnotation(builder.toString(), Color.GRAY), result);
							instr.setEliminated(true);
						}
					}
					catch (NumberFormatException nfe)
					{
						logger.error("Couldn't parse BCI", nfe);
					}
				}

			}

			break;
		}
	}

	private void buildParseTagAnnotations(Tag parseTag, Map<Integer, LineAnnotation> result,
			List<BytecodeInstruction> instructions, CompilerName compilerName) throws AnnotationException
	{
		if (DEBUG_LOGGING)
		{
			logger.debug("Building parse tag annotations");
		}

		List<Tag> children = parseTag.getChildren();

		int currentBytecode = -1;

		Map<String, String> methodAttrs = new HashMap<>();
		Map<String, String> callAttrs = new HashMap<>();

		boolean isC2 = false;

		if (compilerName == CompilerName.C2)
		{
			isC2 = true;
		}

		boolean inMethod = true;
		BytecodeInstruction currentInstruction = null;

		for (Tag child : children)
		{
			String name = child.getName();
			Map<String, String> tagAttrs = child.getAttrs();

			if (DEBUG_LOGGING)
			{
				logger.debug("Examining child tag {}", child);
			}

			switch (name)
			{
			case TAG_BC:
			{
				String bciAttr = tagAttrs.get(ATTR_BCI);
				String codeAttr = tagAttrs.get(ATTR_CODE);

				currentBytecode = Integer.parseInt(bciAttr);
				int code = Integer.parseInt(codeAttr);
				callAttrs.clear();

				// TODO fix this old logic

				// we found a LogCompilation bc tag
				// e.g. "<bc code='182' bci='2'/>"
				// Now check in the current class bytecode
				// that the instruction at offset bci
				// has the same opcode as attribute code
				// if not then this is probably a TieredCompilation
				// context change. (TieredCompilation does not use
				// nested parse tags so have to use this heuristic
				// to check if we are still in the same method.

				if (DEBUG_LOGGING_BYTECODE)
				{
					logger.debug("BC Tag {} {}", currentBytecode, code);
				}

				currentInstruction = getInstructionAtIndex(instructions, currentBytecode);

				if (DEBUG_LOGGING_BYTECODE)
				{
					logger.debug("Instruction at {} is {}", currentBytecode, currentInstruction);
				}

				inMethod = false;

				if (currentInstruction != null)
				{
					int opcodeValue = currentInstruction.getOpcode().getValue();

					if (opcodeValue == code)
					{
						inMethod = true;
					}
				}
			}
				break;
			case TAG_CALL:
			{
				callAttrs.clear();
				callAttrs.putAll(tagAttrs);
			}
				break;
			case TAG_METHOD:
			{
				methodAttrs.clear();
				methodAttrs.putAll(tagAttrs);

				String nameAttr = methodAttrs.get(ATTR_NAME);

				inMethod = false;

				if (nameAttr != null && currentInstruction != null && currentInstruction.hasComment())
				{
					String comment = currentInstruction.getComment();

					inMethod = comment.contains(nameAttr);
				}
			}
				break;
			case TAG_INLINE_SUCCESS:
			{
				if (inMethod || isC2)
				{
					if (!sanityCheckInline(currentInstruction))
					{
						throw new AnnotationException("Expected an invoke instruction (in INLINE_SUCCESS)", currentBytecode,
								currentInstruction);
					}

					String reason = tagAttrs.get(ATTR_REASON);
					String annotationText = InlineUtil.buildInlineAnnotationText(true, reason, callAttrs, methodAttrs);

					storeAnnotation(currentBytecode, new LineAnnotation(annotationText, Color.GREEN), result);
				}
			}
				break;
			case TAG_INLINE_FAIL:
			{
				if (inMethod || isC2)
				{
					if (!sanityCheckInline(currentInstruction))
					{
						throw new AnnotationException("Expected an invoke instruction (in INLINE_FAIL)", currentBytecode,
								currentInstruction);
					}

					String reason = tagAttrs.get(ATTR_REASON);
					String annotationText = InlineUtil.buildInlineAnnotationText(false, reason, callAttrs, methodAttrs);

					storeAnnotation(currentBytecode, new LineAnnotation(annotationText, Color.RED), result);
				}
			}
				break;
			case TAG_BRANCH:
			{
				if (!result.containsKey(currentBytecode))
				{
					if (inMethod || isC2)
					{
						if (!sanityCheckBranch(currentInstruction))
						{
							throw new AnnotationException("Expected a branch instruction (in BRANCH)", currentBytecode,
									currentInstruction);
						}

						String branchAnnotation = buildBranchAnnotation(tagAttrs);

						storeAnnotation(currentBytecode, new LineAnnotation(branchAnnotation, Color.BLUE), result);
					}
				}
			}
				break;
			case TAG_INTRINSIC:
			{
				if (inMethod || isC2)
				{
					if (!sanityCheckIntrinsic(currentInstruction))
					{
						for (BytecodeInstruction ins : instructions)
						{
							logger.info("! instruction: {}", ins);
						}

						throw new AnnotationException("Expected an invoke instruction (IN INTRINSIC)", currentBytecode,
								currentInstruction);
					}

					StringBuilder reason = new StringBuilder();
					reason.append("Intrinsic: ").append(tagAttrs.get(ATTR_ID));

					storeAnnotation(currentBytecode, new LineAnnotation(reason.toString(), Color.GREEN), result);
				}
			}
				break;

			default:
				break;
			}
		}
	}

	private void storeAnnotation(int bci, LineAnnotation annotation, Map<Integer, LineAnnotation> result)
	{
		if (DEBUG_LOGGING)
		{
			logger.debug("BCI: {} Anno: {}", bci, annotation.getAnnotation());
		}

		result.put(bci, annotation);
	}

	private String buildBranchAnnotation(Map<String, String> tagAttrs)
	{
		String count = tagAttrs.get(ATTR_BRANCH_COUNT);
		String taken = tagAttrs.get(ATTR_BRANCH_TAKEN);
		String notTaken = tagAttrs.get(ATTR_BRANCH_NOT_TAKEN);
		String prob = tagAttrs.get(ATTR_BRANCH_PROB);

		StringBuilder reason = new StringBuilder();

		if (count != null)
		{
			reason.append("Count: ").append(count).append(C_NEWLINE);
		}

		reason.append("Branch taken: ").append(taken).append(C_NEWLINE).append("Branch not taken: ").append(notTaken);

		if (prob != null)
		{
			reason.append(C_NEWLINE).append("Taken Probability: ").append(prob);
		}

		return reason.toString();
	}

	// used to detect if class file matches log file
	// only these bytecode instruction should be at the offset
	// for an inlining log statement
	public static boolean sanityCheckInline(BytecodeInstruction instr)
	{
		return sanityCheckInvoke(instr);
	}

	public static boolean sanityCheckIntrinsic(BytecodeInstruction instr)
	{
		return sanityCheckInvoke(instr);
	}

	private static boolean sanityCheckInvoke(BytecodeInstruction instr)
	{
		boolean sane = false;

		if (instr != null)
		{
			sane = instr.isInvoke();
		}

		return sane;
	}

	public static boolean sanityCheckBranch(BytecodeInstruction instr)
	{
		boolean sane = false;

		if (instr != null)
		{
			sane = instr.getOpcode().getMnemonic().startsWith("if");
		}

		return sane;
	}

	private BytecodeInstruction getInstructionAtIndex(List<BytecodeInstruction> instructions, int index)
	{
		BytecodeInstruction found = null;

		for (BytecodeInstruction instruction : instructions)
		{
			if (instruction.getOffset() == index)
			{
				found = instruction;
				break;
			}
		}

		return found;
	}
}

File: src/main/java/org/adoptopenjdk/jitwatch/ui/triview/bytecode/ViewerBytecode.java
/*
 * Copyright (c) 2013, 2014 Chris Newland.
 * Licensed under https://github.com/AdoptOpenJDK/jitwatch/blob/master/LICENSE-BSD
 * Instructions: https://github.com/AdoptOpenJDK/jitwatch/wiki
 */
package org.adoptopenjdk.jitwatch.ui.triview.bytecode;

import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_SEMICOLON;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_NEWLINE;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javafx.application.Platform;
import javafx.event.EventHandler;
import javafx.scene.control.Label;
import javafx.scene.control.Tooltip;
import javafx.scene.input.MouseButton;
import javafx.scene.input.MouseEvent;
import javafx.scene.paint.Color;

import org.adoptopenjdk.jitwatch.model.AnnotationException;
import org.adoptopenjdk.jitwatch.model.IMetaMember;
import org.adoptopenjdk.jitwatch.model.IReadOnlyJITDataModel;
import org.adoptopenjdk.jitwatch.model.LineAnnotation;
import org.adoptopenjdk.jitwatch.model.bytecode.BytecodeAnnotationBuilder;
import org.adoptopenjdk.jitwatch.model.bytecode.BytecodeInstruction;
import org.adoptopenjdk.jitwatch.model.bytecode.ClassBC;
import org.adoptopenjdk.jitwatch.model.bytecode.MemberBytecode;
import org.adoptopenjdk.jitwatch.model.bytecode.Opcode;
import org.adoptopenjdk.jitwatch.suggestion.Suggestion;
import org.adoptopenjdk.jitwatch.suggestion.Suggestion.SuggestionType;
import org.adoptopenjdk.jitwatch.ui.IStageAccessProxy;
import org.adoptopenjdk.jitwatch.ui.triview.ILineListener;
import org.adoptopenjdk.jitwatch.ui.triview.ILineListener.LineType;
import org.adoptopenjdk.jitwatch.ui.triview.TriViewNavigationStack;
import org.adoptopenjdk.jitwatch.ui.triview.Viewer;
import org.adoptopenjdk.jitwatch.util.JVMSUtil;
import org.adoptopenjdk.jitwatch.util.ParseUtil;
import org.adoptopenjdk.jitwatch.util.StringUtil;

public class ViewerBytecode extends Viewer
{
	private List<BytecodeInstruction> instructions = new ArrayList<>();

	private boolean offsetMismatchDetected = false;
	private IReadOnlyJITDataModel model;
	private TriViewNavigationStack navigationStack;
	private Suggestion lastSuggestion = null;

	public ViewerBytecode(IStageAccessProxy stageAccessProxy, TriViewNavigationStack navigationStack, IReadOnlyJITDataModel model,
			ILineListener lineListener, LineType lineType)
	{
		super(stageAccessProxy, lineListener, lineType, true);
		this.model = model;
		this.navigationStack = navigationStack;
	}

	public void highlightBytecodeForSuggestion(Suggestion suggestion)
	{
		lastSuggestion = suggestion;

		int bytecodeOffset = suggestion.getBytecodeOffset();

		int index = getLineIndexForBytecodeOffset(bytecodeOffset);

		BytecodeLabel labelAtIndex = (BytecodeLabel) getLabelAtIndex(index);

		if (labelAtIndex != null)
		{
			StringBuilder ttBuilder = new StringBuilder();

			Tooltip tooltip = labelAtIndex.getTooltip();

			if (tooltip != null)
			{
				ttBuilder.append(tooltip.getText()).append(S_NEWLINE).append(S_NEWLINE);
				Tooltip.uninstall(labelAtIndex, tooltip);
			}

			ttBuilder.append("Suggestion:\n");

			String text = suggestion.getText();

			if (suggestion.getType() == SuggestionType.BRANCH)
			{
				text = StringUtil.wordWrap(text, 50);
			}

			ttBuilder.append(text);

			tooltip = new Tooltip(ttBuilder.toString());
			labelAtIndex.setTooltip(tooltip);
		}

		highlightLine(index);
	}

	public void highlightBytecodeOffset(int bci)
	{
		int index = getLineIndexForBytecodeOffset(bci);
		highlightLine(index);
	}

	public void setContent(final IMetaMember member, final ClassBC metaClassBytecode, final List<String> classLocations)
	{
		offsetMismatchDetected = false;

		if (metaClassBytecode != null)
		{
			MemberBytecode memberBytecode = metaClassBytecode.getMemberBytecode(member);

			if (memberBytecode != null)
			{
				instructions = memberBytecode.getInstructions();
			}
		}

		Map<Integer, LineAnnotation> annotations = new HashMap<Integer, LineAnnotation>();

		lineAnnotations.clear();
		lastScrollIndex = -1;

		List<Label> labels = new ArrayList<>();

		if (instructions != null && instructions.size() > 0)
		{
			try
			{
				annotations = new BytecodeAnnotationBuilder().buildBytecodeAnnotations(member, instructions);
			}
			catch (AnnotationException annoEx)
			{
				logger.error("class bytecode mismatch: {}", annoEx.getMessage());
				logger.error("Member was {}", member);
				offsetMismatchDetected = true;
			}

			int maxOffset = instructions.get(instructions.size() - 1).getOffset();

			int lineIndex = 0;

			for (final BytecodeInstruction instruction : instructions)
			{
				int labelLines = instruction.getLabelLines();

				if (labelLines == 0)
				{
					BytecodeLabel lblLine = createLabel(instruction, maxOffset, 0, annotations, member, lineIndex++);
					labels.add(lblLine);
				}
				else
				{
					for (int i = 0; i < labelLines; i++)
					{
						BytecodeLabel lblLine = createLabel(instruction, maxOffset, i, annotations, member, lineIndex++);
						labels.add(lblLine);
					}
				}
			}
		}

		setContent(labels);

		checkIfExistingSuggestionForMember(member);
	}

	private void checkIfExistingSuggestionForMember(IMetaMember member)
	{
		if (lastSuggestion != null && lastSuggestion.getCaller().equals(member))
		{
			highlightBytecodeForSuggestion(lastSuggestion);
		}
	}

	private BytecodeLabel createLabel(final BytecodeInstruction instruction, int maxOffset, int line,
			final Map<Integer, LineAnnotation> annotations, final IMetaMember member, final int lineIndex)
	{
		BytecodeLabel lblLine = new BytecodeLabel(instruction, maxOffset, line);

		int offset = instruction.getOffset();

		StringBuilder instructionToolTipBuilder = new StringBuilder();

		String unhighlightedStyle = STYLE_UNHIGHLIGHTED;

		if (annotations != null)
		{
			LineAnnotation annotation = annotations.get(offset);

			if (annotation != null)
			{
				Color colour = annotation.getColour();

				unhighlightedStyle = STYLE_UNHIGHLIGHTED + "-fx-text-fill:" + toRGBCode(colour) + C_SEMICOLON;

				instructionToolTipBuilder = new StringBuilder();
				instructionToolTipBuilder.append(annotation.getAnnotation());
			}
		}

		lblLine.setUnhighlightedStyle(unhighlightedStyle);

		if (instruction.isEliminated())
		{
			lblLine.getStyleClass().add("eliminated-allocation");
		}
		
		if (instruction.isInvoke())
		{
			if (instructionToolTipBuilder.length() > 0)
			{
				instructionToolTipBuilder.append(S_NEWLINE).append(S_NEWLINE);
			}

			instructionToolTipBuilder.append("Ctrl-click to inspect this method\nBackspace to return");
		}

		if (instructionToolTipBuilder.length() > 0)
		{
			Tooltip toolTip = new Tooltip(instructionToolTipBuilder.toString());

			toolTip.setStyle("-fx-strikethrough: false;");
			toolTip.getStyleClass().clear();
			toolTip.getStyleClass().add("tooltip");
			lblLine.setTooltip(toolTip);
		}

		lblLine.setOnMouseClicked(new EventHandler<MouseEvent>()
		{
			@Override
			public void handle(MouseEvent mouseEvent)
			{
				if (mouseEvent.getButton().equals(MouseButton.PRIMARY))
				{
					if (mouseEvent.getClickCount() == 2)
					{
						Opcode opcode = instruction.getOpcode();

						browseMnemonic(opcode);
					}
					else if (mouseEvent.getClickCount() == 1)
					{
						handleNavigate(member, instruction, lineIndex);
					}
				}
			}
		});

		return lblLine;
	}

	private void handleNavigate(IMetaMember currentMember, BytecodeInstruction instruction, int lineIndex)
	{
		if (navigationStack.isCtrlPressed())
		{
			if (instruction != null && instruction.isInvoke())
			{
				try
				{
					IMetaMember member = ParseUtil.getMemberFromBytecodeComment(model, currentMember, instruction);

					if (member != null)
					{
						navigationStack.navigateTo(member);
					}
				}
				catch (Exception ex)
				{
					logger.error("Could not calculate member for instruction: {}", instruction, ex);
				}
			}
		}
		else
		{
			clearAllHighlighting();

			lineListener.lineHighlighted(lineIndex, lineType);
			highlightLine(lineIndex);
		}
	}

	public boolean isOffsetMismatchDetected()
	{
		return offsetMismatchDetected;
	}

	public int getLineIndexForBytecodeOffset(int bci)
	{
		int result = -1;

		int pos = 0;

		for (BytecodeInstruction instruction : instructions)
		{
			if (instruction.getOffset() == bci)
			{
				result = pos;
				break;
			}

			pos += instruction.getLabelLines();
		}

		return result;
	}

	private String toRGBCode(Color color)
	{
		return String.format("#%02X%02X%02X", (int) (color.getRed() * 255), (int) (color.getGreen() * 255),
				(int) (color.getBlue() * 255));
	}

	private void browseMnemonic(final Opcode opcode)
	{
		if (JVMSUtil.hasLocalJVMS())
		{
			if (!JVMSUtil.isJVMSLoaded())
			{
				JVMSUtil.loadJVMS();
			}

			String html = JVMSUtil.getBytecodeDescriptions(opcode);

			String cssURI = JVMSUtil.getJVMSCSSURL();

			stageAccessProxy.openBrowser("JMVS Browser - " + opcode.getMnemonic(), html, cssURI);
		}
		else
		{
			stageAccessProxy.openBrowser("Fetching JVM Spec", "Downloading a local copy of the JVM Specification", null);

			new Thread(new Runnable()
			{
				@Override
				public void run()
				{
					boolean success = JVMSUtil.fetchJVMS();

					if (success)
					{
						downloadJVMSpecAndShowOpcode(opcode);
					}
					else
					{
						showDownloadFailure();
					}
				}
			}).start();
		}
	}

	private void downloadJVMSpecAndShowOpcode(final Opcode opcode)
	{
		JVMSUtil.loadJVMS();

		final String html = JVMSUtil.getBytecodeDescriptions(opcode);

		final String cssURI = JVMSUtil.getJVMSCSSURL();

		Platform.runLater(new Runnable()
		{
			@Override
			public void run()
			{
				stageAccessProxy.openBrowser("JMVS Browser - " + opcode.getMnemonic(), html, cssURI);
			}
		});
	}

	private void showDownloadFailure()
	{
		Platform.runLater(new Runnable()
		{
			@Override
			public void run()
			{
				stageAccessProxy
						.openBrowser("Downloading Failed", "Unable to download a local copy of the JVM Specification", null);
			}
		});
	}
}

File: src/main/java/org/adoptopenjdk/jitwatch/util/ParseUtil.java
/*
 * Copyright (c) 2013, 2014 Chris Newland.
 * Licensed under https://github.com/AdoptOpenJDK/jitwatch/blob/master/LICENSE-BSD
 * Instructions: https://github.com/AdoptOpenJDK/jitwatch/wiki
 */
package org.adoptopenjdk.jitwatch.util;

import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_ARGUMENTS;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_HOLDER;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_NAME;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_RETURN;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_CLOSE_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_DOT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_OBJECT_REF;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_OPEN_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_OPEN_SQUARE_BRACKET;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_QUOTE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_SEMICOLON;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_SLASH;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_SPACE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.DEBUG_LOGGING;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.DEBUG_LOGGING_OVC;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.DEBUG_LOGGING_SIG_MATCH;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_ARRAY_BRACKET_PAIR;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CLASS;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CLASS_AUTOGENERATED_LAMBDA;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CLOSE_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CLOSE_PARENTHESES;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_DOT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_EMPTY;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_ENTITY_GT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_ENTITY_LT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_NEWLINE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_OBJECT_ARRAY_DEF;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_OPEN_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_OPEN_PARENTHESES;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_PACKAGE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_SEMICOLON;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_SLASH;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_SPACE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_BOOLEAN;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_BYTE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_CHARACTER;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_DOUBLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_FLOAT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_INTEGER;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_LONG;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_SHORT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_TYPE_NAME_VOID;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_VARARGS_DOTS;

import java.text.NumberFormat;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.adoptopenjdk.jitwatch.core.JITWatchConstants;
import org.adoptopenjdk.jitwatch.model.IMetaMember;
import org.adoptopenjdk.jitwatch.model.IParseDictionary;
import org.adoptopenjdk.jitwatch.model.IReadOnlyJITDataModel;
import org.adoptopenjdk.jitwatch.model.LogParseException;
import org.adoptopenjdk.jitwatch.model.MemberSignatureParts;
import org.adoptopenjdk.jitwatch.model.MetaClass;
import org.adoptopenjdk.jitwatch.model.PackageManager;
import org.adoptopenjdk.jitwatch.model.Tag;
import org.adoptopenjdk.jitwatch.model.bytecode.BytecodeInstruction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class ParseUtil
{
	private static final Logger logger = LoggerFactory.getLogger(ParseUtil.class);

	// class<SPACE>METHOD<SPACE>(PARAMS)RETURN

	// http://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html#jvms-4.2
	public static String CLASS_NAME_REGEX_GROUP = "([^;\\[/<>]+)";
	public static String METHOD_NAME_REGEX_GROUP = "([^;\\[/]+)";

	public static String PARAM_REGEX_GROUP = "(\\(.*\\))";
	public static String RETURN_REGEX_GROUP = "(.*)";

	private static final Pattern PATTERN_LOG_SIGNATURE = Pattern.compile("^" + CLASS_NAME_REGEX_GROUP + " "
			+ METHOD_NAME_REGEX_GROUP + " " + PARAM_REGEX_GROUP + RETURN_REGEX_GROUP);

	public static final char TYPE_SHORT = 'S';
	public static final char TYPE_CHARACTER = 'C';
	public static final char TYPE_BYTE = 'B';
	public static final char TYPE_VOID = 'V';
	public static final char TYPE_LONG = 'J';
	public static final char TYPE_DOUBLE = 'D';
	public static final char TYPE_BOOLEAN = 'Z';
	public static final char TYPE_INTEGER = 'I';
	public static final char TYPE_FLOAT = 'F';

	private ParseUtil()
	{
	}

	public static long parseStamp(String stamp)
	{
		long result = 0;

		if (stamp != null)
		{
			double number = parseLocaleSafeDouble(stamp);

			result = (long) (number * 1000);
		}
		else
		{
			logger.warn("Could not parse null stamp");
		}

		return result;
	}

	public static double parseLocaleSafeDouble(String str)
	{
		NumberFormat nf = NumberFormat.getInstance(Locale.getDefault());

		double result = 0;

		try
		{
			result = nf.parse(str).doubleValue();
		}
		catch (ParseException pe)
		{
			logger.error("", pe);
		}

		return result;
	}

	public static Class<?> getPrimitiveClass(char c)
	{
		switch (c)
		{
		case TYPE_SHORT:
			return Short.TYPE;
		case TYPE_CHARACTER:
			return Character.TYPE;
		case TYPE_BYTE:
			return Byte.TYPE;
		case TYPE_VOID:
			return Void.TYPE;
		case TYPE_LONG:
			return Long.TYPE;
		case TYPE_DOUBLE:
			return Double.TYPE;
		case TYPE_BOOLEAN:
			return Boolean.TYPE;
		case TYPE_INTEGER:
			return Integer.TYPE;
		case TYPE_FLOAT:
			return Float.TYPE;
		}

		throw new RuntimeException("Unknown class for " + c);
	}

	/*
	 * [C => char[] [[I => int[][] [Ljava.lang.Object; => java.lang.Object[]
	 */
	public static String expandParameterType(String name)
	{
		StringBuilder builder = new StringBuilder();

		int arrayDepth = 0;
		int pos = 0;

		outerloop: while (pos < name.length())
		{
			char c = name.charAt(pos);

			switch (c)
			{
			case C_OPEN_SQUARE_BRACKET:
				arrayDepth++;
				break;
			case TYPE_SHORT:
				builder.append(S_TYPE_NAME_SHORT);
				break;
			case TYPE_CHARACTER:
				builder.append(S_TYPE_NAME_CHARACTER);
				break;
			case TYPE_BYTE:
				builder.append(S_TYPE_NAME_BYTE);
				break;
			case TYPE_LONG:
				builder.append(S_TYPE_NAME_LONG);
				break;
			case TYPE_DOUBLE:
				builder.append(S_TYPE_NAME_DOUBLE);
				break;
			case TYPE_BOOLEAN:
				builder.append(S_TYPE_NAME_BOOLEAN);
				break;
			case TYPE_INTEGER:
				builder.append(S_TYPE_NAME_INTEGER);
				break;
			case TYPE_FLOAT:
				builder.append(S_TYPE_NAME_FLOAT);
				break;
			case C_SEMICOLON:
				break;
			default:
				if (name.charAt(pos) == C_OBJECT_REF && name.endsWith(S_SEMICOLON))
				{
					builder.append(name.substring(pos + 1, name.length() - 1));
				}
				else
				{
					builder.append(name.substring(pos));
				}
				break outerloop;
			}

			pos++;
		}

		for (int i = 0; i < arrayDepth; i++)
		{
			builder.append(S_ARRAY_BRACKET_PAIR);
		}

		return builder.toString();
	}

	public static String[] splitLogSignatureWithRegex(final String logSignature) throws LogParseException
	{
		String sig = logSignature;

		sig = sig.replace(S_ENTITY_LT, S_OPEN_ANGLE);
		sig = sig.replace(S_ENTITY_GT, S_CLOSE_ANGLE);

		Matcher matcher = PATTERN_LOG_SIGNATURE.matcher(sig);

		if (matcher.find())
		{
			String className = matcher.group(1);
			String methodName = matcher.group(2);
			String paramTypes = matcher.group(3).replace(S_OPEN_PARENTHESES, S_EMPTY).replace(S_CLOSE_PARENTHESES, S_EMPTY);
			String returnType = matcher.group(4);

			return new String[] { className, methodName, paramTypes, returnType };
		}

		throw new LogParseException("Could not split signature with regex: '" + logSignature + C_QUOTE);
	}

	public static IMetaMember findMemberWithSignature(IReadOnlyJITDataModel model, String logSignature) throws LogParseException
	{
		IMetaMember metaMember = null;

		if (logSignature != null)
		{
			MemberSignatureParts msp = MemberSignatureParts.fromLogCompilationSignature(logSignature);

			metaMember = model.findMetaMember(msp);

			if (metaMember == null)
			{
				throw new LogParseException("MetaMember not found for " + logSignature);
			}
		}

		return metaMember;
	}

	public static Class<?>[] getClassTypes(String typesString) throws LogParseException
	{
		List<Class<?>> classes = new ArrayList<Class<?>>();

		if (typesString.length() > 0)
		{
			try
			{
				findClassesForTypeString(typesString, classes);
			}
			catch (Throwable t)
			{
				throw new LogParseException("Could not parse types: " + typesString, t);
			}

		} // end if empty

		return classes.toArray(new Class<?>[classes.size()]);
	}

	public static Class<?> findClassForLogCompilationParameter(String param) throws ClassNotFoundException
	{
		StringBuilder builder = new StringBuilder();

		if (isPrimitive(param))
		{
			return classForPrimitive(param);
		}
		else
		{
			int arrayBracketCount = getArrayBracketCount(param);

			if (param.contains(S_CLOSE_ANGLE))
			{
				param = stripGenerics(param);
			}

			if (arrayBracketCount == 0)
			{
				if (param.endsWith(S_VARARGS_DOTS))
				{
					String partBeforeDots = param.substring(0, param.length() - S_VARARGS_DOTS.length());

					if (isPrimitive(partBeforeDots))
					{
						builder.append(S_OPEN_ANGLE).append(classForPrimitive(partBeforeDots));
					}
					else
					{
						builder.append(S_OBJECT_ARRAY_DEF).append(partBeforeDots);
						builder.append(C_SEMICOLON);
					}
				}
				else
				{
					builder.append(param);
				}
			}
			else
			{
				int arrayBracketChars = 2 * arrayBracketCount;

				String partBeforeArrayBrackets = param.substring(0, param.length() - arrayBracketChars);

				for (int i = 0; i < arrayBracketCount - 1; i++)
				{
					builder.append(C_OPEN_SQUARE_BRACKET);
				}

				if (isPrimitive(partBeforeArrayBrackets))
				{
					builder.append(C_OPEN_SQUARE_BRACKET);

					builder.append(getClassTypeCharForPrimitiveTypeString(partBeforeArrayBrackets));
				}
				else
				{
					builder.append(S_OBJECT_ARRAY_DEF);

					builder.append(param);

					builder.delete(builder.length() - arrayBracketChars, builder.length());

					builder.append(C_SEMICOLON);
				}
			}

			return ClassUtil.loadClassWithoutInitialising(builder.toString());
		}
	}

	public static String stripGenerics(String param)
	{
		String result = param;

		if (param != null)
		{
			int firstOpenAngle = param.indexOf(C_OPEN_ANGLE);
			int lastCloseAngle = param.lastIndexOf(C_CLOSE_ANGLE);

			if (firstOpenAngle != -1 && lastCloseAngle != -1 && firstOpenAngle < lastCloseAngle)
			{
				result = param.substring(0, firstOpenAngle) + param.substring(lastCloseAngle + 1);
			}
		}

		return result;
	}

	public static boolean paramClassesMatch(boolean memberHasVarArgs, List<Class<?>> memberParamClasses,
			List<Class<?>> signatureParamClasses, boolean matchTypesExactly)
	{
		boolean result = true;

		final int memberParamCount = memberParamClasses.size();
		final int signatureParamCount = signatureParamClasses.size();

		if (DEBUG_LOGGING_SIG_MATCH)
		{
			logger.debug("MemberParamCount:{} SignatureParamCount:{} varArgs:{}", memberParamCount, signatureParamCount,
					memberHasVarArgs);
		}

		if (!memberHasVarArgs && memberParamCount != signatureParamCount)
		{
			result = false;
		}
		else if (memberParamCount > 0 && signatureParamCount > 0)
		{
			int memPos = memberParamCount - 1;

			for (int sigPos = signatureParamCount - 1; sigPos >= 0; sigPos--)
			{
				Class<?> sigParamClass = signatureParamClasses.get(sigPos);

				Class<?> memParamClass = memberParamClasses.get(memPos);

				boolean memberParamCouldBeVarArgs = false;

				boolean isLastParameter = (memPos == memberParamCount - 1);

				if (memberHasVarArgs && isLastParameter)
				{
					memberParamCouldBeVarArgs = true;
				}

				boolean classMatch = false;

				if (matchTypesExactly)
				{
					classMatch = memParamClass.equals(sigParamClass);
				}
				else
				{
					classMatch = memParamClass.isAssignableFrom(sigParamClass);
				}

				if (classMatch)
				{
					if (DEBUG_LOGGING_SIG_MATCH)
					{
						logger.debug("{} equals/isAssignableFrom {}", memParamClass, sigParamClass);
					}

					if (memPos > 0)
					{
						// move to previous member parameter
						memPos--;
					}
					else if (sigPos > 0)
					{
						if (DEBUG_LOGGING_SIG_MATCH)
						{
							logger.debug("More signature params but no more member params to try");
						}

						result = false;
						break;
					}
				}
				else
				{
					if (memberParamCouldBeVarArgs)
					{
						// check assignable
						Class<?> componentType = memParamClass.getComponentType();

						if (!componentType.isAssignableFrom(sigParamClass))
						{
							result = false;
							break;
						}
					}
					else
					{
						result = false;
						break;
					}

				} // if classMatch

			} // for

			boolean unusedMemberParams = (memPos > 0);

			if (unusedMemberParams)
			{
				result = false;
			}
		}

		return result;
	}

	public static boolean typeIsVarArgs(String type)
	{
		return type != null && type.endsWith(S_VARARGS_DOTS);
	}

	public static char getClassTypeCharForPrimitiveTypeString(String type)
	{
		switch (type)
		{
		case S_TYPE_NAME_INTEGER:
			return TYPE_INTEGER;
		case S_TYPE_NAME_BOOLEAN:
			return TYPE_BOOLEAN;
		case S_TYPE_NAME_LONG:
			return TYPE_LONG;
		case S_TYPE_NAME_DOUBLE:
			return TYPE_DOUBLE;
		case S_TYPE_NAME_FLOAT:
			return TYPE_FLOAT;
		case S_TYPE_NAME_SHORT:
			return TYPE_SHORT;
		case S_TYPE_NAME_BYTE:
			return TYPE_BYTE;
		case S_TYPE_NAME_CHARACTER:
			return TYPE_CHARACTER;
		case S_TYPE_NAME_VOID:
			return TYPE_VOID;
		}

		throw new RuntimeException(type + " is not a primitive type");
	}

	public static boolean isPrimitive(String type)
	{
		boolean result = false;

		if (type != null)
		{
			switch (type)
			{
			case S_TYPE_NAME_INTEGER:
			case S_TYPE_NAME_BOOLEAN:
			case S_TYPE_NAME_LONG:
			case S_TYPE_NAME_DOUBLE:
			case S_TYPE_NAME_FLOAT:
			case S_TYPE_NAME_SHORT:
			case S_TYPE_NAME_BYTE:
			case S_TYPE_NAME_CHARACTER:
			case S_TYPE_NAME_VOID:
				result = true;
			}
		}

		return result;
	}

	public static Class<?> classForPrimitive(String primitiveType)
	{
		if (primitiveType != null)
		{
			switch (primitiveType)
			{
			case S_TYPE_NAME_INTEGER:
				return int.class;
			case S_TYPE_NAME_BOOLEAN:
				return boolean.class;
			case S_TYPE_NAME_LONG:
				return long.class;
			case S_TYPE_NAME_DOUBLE:
				return double.class;
			case S_TYPE_NAME_FLOAT:
				return float.class;
			case S_TYPE_NAME_SHORT:
				return short.class;
			case S_TYPE_NAME_BYTE:
				return byte.class;
			case S_TYPE_NAME_CHARACTER:
				return char.class;
			case S_TYPE_NAME_VOID:
				return void.class;
			}
		}

		throw new RuntimeException(primitiveType + " is not a primitive type");
	}

	public static int getArrayBracketCount(String param)
	{
		int count = 0;

		if (param != null)
		{
			int index = param.indexOf(S_ARRAY_BRACKET_PAIR, 0);

			while (index != -1)
			{
				count++;

				index = param.indexOf(S_ARRAY_BRACKET_PAIR, index + 2);
			}
		}

		return count;
	}

	/*
	 * Converts (III[Ljava.lang.String;) into a list of Class<?>
	 */
	private static void findClassesForTypeString(final String typesString, List<Class<?>> classes) throws ClassNotFoundException
	{
		// logger.debug("Parsing: {}", typesString);

		String toParse = typesString.replace(C_SLASH, C_DOT);

		int pos = 0;

		StringBuilder builder = new StringBuilder();

		final int stringLen = toParse.length();

		while (pos < stringLen)
		{
			char c = toParse.charAt(pos);

			switch (c)
			{
			case C_OPEN_SQUARE_BRACKET:
				// Could be
				// [Ljava.lang.String; Object array
				// [I primitive array
				// [..[I multidimensional primitive array
				// [..[Ljava.lang.String multidimensional Object array
				builder.delete(0, builder.length());
				builder.append(c);
				pos++;
				c = toParse.charAt(pos);

				while (c == C_OPEN_SQUARE_BRACKET)
				{
					builder.append(c);
					pos++;
					c = toParse.charAt(pos);
				}

				if (c == C_OBJECT_REF)
				{
					// array of ref type
					while (pos < stringLen)
					{
						c = toParse.charAt(pos++);
						builder.append(c);

						if (c == C_SEMICOLON)
						{
							break;
						}
					}
				}
				else
				{
					// array of primitive
					builder.append(c);
					pos++;
				}

				Class<?> arrayClass = ClassUtil.loadClassWithoutInitialising(builder.toString());
				classes.add(arrayClass);
				builder.delete(0, builder.length());
				break;
			case C_OBJECT_REF:
				// ref type
				while (pos < stringLen - 1)
				{
					pos++;
					c = toParse.charAt(pos);

					if (c == C_SEMICOLON)
					{
						pos++;
						break;
					}

					builder.append(c);
				}
				Class<?> refClass = ClassUtil.loadClassWithoutInitialising(builder.toString());
				classes.add(refClass);
				builder.delete(0, builder.length());
				break;
			default:
				// primitive
				Class<?> primitiveClass = ParseUtil.getPrimitiveClass(c);
				classes.add(primitiveClass);
				pos++;

			} // end switch

		} // end while
	}

	public static String findBestMatchForMemberSignature(IMetaMember member, List<String> lines)
	{
		String match = null;

		logger.debug("findBestMatch: {}", member.toString());

		if (lines != null)
		{
			int index = findBestLineMatchForMemberSignature(member, lines);

			if (index > 0 && index < lines.size())
			{
				match = lines.get(index);
			}
		}

		return match;
	}

	public static int findBestLineMatchForMemberSignature(IMetaMember member, List<String> lines)
	{
		int bestScoreLine = 0;

		if (lines != null)
		{
			String memberName = member.getMemberName();
			int modifier = member.getModifier();
			String returnTypeName = member.getReturnTypeName();
			String[] paramTypeNames = member.getParamTypeNames();

			int bestScore = 0;

			for (int i = 0; i < lines.size(); i++)
			{
				String line = lines.get(i);

				int score = 0;

				if (line.contains(memberName))
				{
					if (DEBUG_LOGGING_SIG_MATCH)
					{
						logger.debug("Comparing {} with {}", line, member);
					}

					MemberSignatureParts msp = MemberSignatureParts.fromBytecodeSignature(member.getMetaClass()
							.getFullyQualifiedName(), line);

					if (!memberName.equals(msp.getMemberName()))
					{
						continue;
					}

					// modifiers matched
					if (msp.getModifier() != modifier)
					{
						continue;
					}

					List<String> mspParamTypes = msp.getParamTypes();

					if (mspParamTypes.size() != paramTypeNames.length)
					{
						continue;
					}

					int pos = 0;

					for (String memberParamType : paramTypeNames)
					{
						String mspParamType = msp.getParamTypes().get(pos++);

						if (compareTypeEquality(memberParamType, mspParamType, msp.getGenerics()))
						{
							score++;
						}
					}

					// return type matched
					if (compareTypeEquality(returnTypeName, msp.getReturnType(), msp.getGenerics()))
					{
						score++;
					}

					if (score > bestScore)
					{
						bestScoreLine = i;
						bestScore = score;
					}
				}
			}
		}

		return bestScoreLine;
	}

	private static boolean compareTypeEquality(String memberTypeName, String inMspTypeName, Map<String, String> genericsMap)
	{
		String mspTypeName = inMspTypeName;
		if (memberTypeName != null && memberTypeName.equals(mspTypeName))
		{
			return true;
		}
		else if (mspTypeName != null)
		{
			// Substitute generics to match with non-generic signature
			// public static <T extends java.lang.Object, U extends
			// java.lang.Object> T[] copyOf(U[], int, java.lang.Class<? extends
			// T[]>)";
			// U[] -> java.lang.Object[]
			String mspTypeNameWithoutArray = getParamTypeWithoutArrayBrackets(mspTypeName);
			String genericSubstitution = genericsMap.get(mspTypeNameWithoutArray);

			if (genericSubstitution != null)
			{
				mspTypeName = mspTypeName.replace(mspTypeNameWithoutArray, genericSubstitution);

				if (memberTypeName != null && memberTypeName.equals(mspTypeName))
				{
					return true;
				}
			}
		}

		return false;
	}

	public static String getParamTypeWithoutArrayBrackets(String paramType)
	{
		int bracketsIndex = paramType.indexOf(S_ARRAY_BRACKET_PAIR);

		if (bracketsIndex != -1)
		{
			return paramType.substring(0, bracketsIndex);
		}
		else
		{
			return paramType;
		}
	}

	public static String getMethodTagReturn(Tag methodTag, IParseDictionary parseDictionary)
	{
		String returnTypeId = methodTag.getAttribute(ATTR_RETURN);

		String returnType = lookupType(returnTypeId, parseDictionary);

		return returnType;
	}

	public static List<String> getMethodTagArguments(Tag methodTag, IParseDictionary parseDictionary)
	{
		List<String> result = new ArrayList<>();

		String argumentsTypeId = methodTag.getAttribute(ATTR_ARGUMENTS);

		if (argumentsTypeId != null)
		{
			String[] typeIDs = argumentsTypeId.split(S_SPACE);

			for (String typeID : typeIDs)
			{
				result.add(lookupType(typeID, parseDictionary));
			}
		}

		return result;
	}

	public static IMetaMember lookupMember(String methodId, IParseDictionary parseDictionary, IReadOnlyJITDataModel model)
	{
		IMetaMember result = null;

		Tag methodTag = parseDictionary.getMethod(methodId);

		if (methodTag != null)
		{
			String methodName = methodTag.getAttribute(ATTR_NAME);

			String klassId = methodTag.getAttribute(ATTR_HOLDER);

			Tag klassTag = parseDictionary.getKlass(klassId);

			String metaClassName = klassTag.getAttribute(ATTR_NAME);

			metaClassName = metaClassName.replace(S_SLASH, S_DOT);

			String returnType = getMethodTagReturn(methodTag, parseDictionary);

			List<String> argumentTypes = getMethodTagArguments(methodTag, parseDictionary);

			PackageManager pm = model.getPackageManager();

			MetaClass metaClass = pm.getMetaClass(metaClassName);

			if (metaClass == null)
			{
				if (DEBUG_LOGGING)
				{
					logger.debug("metaClass not found: {}. Attempting classload", metaClassName);
				}

				// Possible that TraceClassLoading did not log this class
				// try to classload and add to model

				Class<?> clazz = null;

				try
				{
					clazz = ClassUtil.loadClassWithoutInitialising(metaClassName);

					if (clazz != null)
					{
						metaClass = model.buildAndGetMetaClass(clazz);
					}
				}
				catch (ClassNotFoundException cnf)
				{
					if (!possibleLambdaMethod(metaClassName))
					{
						logger.error("ClassNotFoundException: '" + metaClassName + C_QUOTE);
					}
				}
				catch (NoClassDefFoundError ncdf)
				{
					logger.error("NoClassDefFoundError: '" + metaClassName + C_SPACE + ncdf.getMessage() + C_QUOTE);
				}
			}

			if (metaClass != null)
			{
				MemberSignatureParts msp = MemberSignatureParts.fromParts(metaClass.getFullyQualifiedName(), methodName,
						returnType, argumentTypes);
				result = metaClass.getMemberForSignature(msp);
			}
			else if (!possibleLambdaMethod(metaClassName))
			{
				logger.error("metaClass not found: {}", metaClassName);
			}
		}

		return result;
	}

	public static boolean possibleLambdaMethod(String fqClassName)
	{
		if (fqClassName.contains(S_CLASS_AUTOGENERATED_LAMBDA))
		{
			return true;
		}
		else
		{
			for (String prefix : JITWatchConstants.getAutoGeneratedClassPrefixes())
			{
				if (fqClassName.startsWith(prefix))
				{
					return true;
				}
			}

			return false;
		}
	}
	
	public static String lookupType(String typeOrKlassID, IParseDictionary parseDictionary)
	{
		String result = null;

		// logger.debug("Looking up type: {}", typeOrKlassID);

		if (typeOrKlassID != null)
		{
			Tag typeTag = parseDictionary.getType(typeOrKlassID);

			// logger.debug("Type? {}", typeTag);

			if (typeTag == null)
			{
				typeTag = parseDictionary.getKlass(typeOrKlassID);

				// logger.debug("Klass? {}", typeTag);
			}

			if (typeTag != null)
			{
				String typeAttrName = typeTag.getAttribute(ATTR_NAME);

				// logger.debug("Name {}", typeAttrName);

				if (typeAttrName != null)
				{
					result = typeAttrName.replace(S_SLASH, S_DOT);

					result = ParseUtil.expandParameterType(result);
				}
			}
		}

		return result;
	}

	public static String getPackageFromSource(String source)
	{
		String result = null;

		String[] lines = source.split(S_NEWLINE);

		for (String line : lines)
		{
			line = line.trim();

			if (line.startsWith(S_PACKAGE) && line.endsWith(S_SEMICOLON))
			{
				result = line.substring(S_PACKAGE.length(), line.length() - 1).trim();
			}
		}

		if (result == null)
		{
			result = S_EMPTY;
		}

		return result;
	}

	public static String getClassFromSource(String source)
	{
		String result = null;

		String[] lines = source.split(S_NEWLINE);

		String classToken = S_SPACE + S_CLASS + S_SPACE;

		for (String line : lines)
		{
			line = line.trim();

			int classTokenPos = line.indexOf(classToken);

			if (classTokenPos != -1)
			{
				result = line.substring(classTokenPos + classToken.length());
			}
		}

		if (result == null)
		{
			result = "";
		}

		return result;
	}

	private static boolean commentMethodHasNoClassPrefix(String comment)
	{
		return (comment.indexOf(C_DOT) == -1);
	}

	private static String prependCurrentMember(String comment, IMetaMember member)
	{
		String currentClass = member.getMetaClass().getFullyQualifiedName();

		currentClass = currentClass.replace(C_DOT, C_SLASH);

		return currentClass + C_DOT + comment;
	}

	public static IMetaMember getMemberFromBytecodeComment(IReadOnlyJITDataModel model, IMetaMember currentMember,
			BytecodeInstruction instruction) throws LogParseException
	{
		IMetaMember result = null;

		if (DEBUG_LOGGING_OVC)
		{
			logger.debug("Looking for member in {} using {}", currentMember, instruction);
		}

		if (instruction != null)
		{
			String comment = instruction.getCommentWithMemberPrefixStripped();

			if (comment != null)
			{
				if (commentMethodHasNoClassPrefix(comment) && currentMember != null)
				{
					comment = prependCurrentMember(comment, currentMember);
				}

				MemberSignatureParts msp = MemberSignatureParts.fromBytecodeComment(comment);

				result = model.findMetaMember(msp);
			}
		}

		return result;
	}
}


File: src/test/java/org/adoptopenjdk/jitwatch/test/TestBytecodeAnnotationBuilder.java
/*
 * Copyright (c) 2013, 2014 Chris Newland.
 * Licensed under https://github.com/AdoptOpenJDK/jitwatch/blob/master/LICENSE-BSD
 * Instructions: https://github.com/AdoptOpenJDK/jitwatch/wiki
 */
package org.adoptopenjdk.jitwatch.test;

import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.*;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_ID;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_METHOD;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_NAME;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.ATTR_RETURN;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_DOT;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.C_SLASH;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_CLOSE_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_NEWLINE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.S_OPEN_ANGLE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_KLASS;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_METHOD;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_PARSE;
import static org.adoptopenjdk.jitwatch.core.JITWatchConstants.TAG_TYPE;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javafx.scene.paint.Color;

import org.adoptopenjdk.jitwatch.core.TagProcessor;
import org.adoptopenjdk.jitwatch.journal.JournalUtil;
import org.adoptopenjdk.jitwatch.loader.BytecodeLoader;
import org.adoptopenjdk.jitwatch.model.AnnotationException;
import org.adoptopenjdk.jitwatch.model.CompilerName;
import org.adoptopenjdk.jitwatch.model.IMetaMember;
import org.adoptopenjdk.jitwatch.model.IParseDictionary;
import org.adoptopenjdk.jitwatch.model.LineAnnotation;
import org.adoptopenjdk.jitwatch.model.ParseDictionary;
import org.adoptopenjdk.jitwatch.model.Tag;
import org.adoptopenjdk.jitwatch.model.bytecode.BytecodeAnnotationBuilder;
import org.adoptopenjdk.jitwatch.model.bytecode.BytecodeInstruction;
import org.adoptopenjdk.jitwatch.model.bytecode.Opcode;
import org.junit.Test;

public class TestBytecodeAnnotationBuilder
{
	@Test
	public void testSanityCheckInlineFail()
	{
		BytecodeInstruction instrAaload = new BytecodeInstruction();
		instrAaload.setOpcode(Opcode.AALOAD);

		assertFalse(BytecodeAnnotationBuilder.sanityCheckInline(instrAaload));
	}

	@Test
	public void testSanityCheckInlinePass()
	{
		BytecodeInstruction instrInvokeSpecial = new BytecodeInstruction();
		instrInvokeSpecial.setOpcode(Opcode.INVOKESPECIAL);

		assertTrue(BytecodeAnnotationBuilder.sanityCheckInline(instrInvokeSpecial));
	}

	@Test
	public void testSanityCheckBranchFail()
	{
		BytecodeInstruction instrAaload = new BytecodeInstruction();
		instrAaload.setOpcode(Opcode.AALOAD);

		assertFalse(BytecodeAnnotationBuilder.sanityCheckBranch(instrAaload));
	}

	@Test
	public void testSanityCheckBranchPass()
	{
		BytecodeInstruction instrIfcmpne = new BytecodeInstruction();
		instrIfcmpne.setOpcode(Opcode.IF_ICMPNE);

		assertTrue(BytecodeAnnotationBuilder.sanityCheckBranch(instrIfcmpne));
	}

	@Test
	public void testJava7NonTieredLeaf()
	{
		String[] logLines = new String[]{
				"<task compile_id='82' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testLeaf (J)V' bytes='66' count='10000' backedge_count='5122' iicount='1' osr_bci='8' stamp='11.372'>",
				"<phase name='parse' nodes='3' live='3' stamp='11.372'>",
				"<type id='636' name='void'/>",
				"<type id='635' name='long'/>",
				"<klass id='729' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='730' holder='729' name='testLeaf' return='636' arguments='635' flags='2' bytes='66' iicount='1'/>",
				"<parse method='730' uses='1' osr_bci='8' stamp='11.372'>",
				"<dependency type='leaf_type' ctxk='729'/>",
				"<dependency type='leaf_type' ctxk='729'/>",
				"<uncommon_trap bci='8' reason='constraint' action='reinterpret'/>",
				"<uncommon_trap bci='8' reason='predicate' action='maybe_recompile'/>",
				"<uncommon_trap bci='8' reason='loop_limit_check' action='maybe_recompile'/>",
				"<bc code='183' bci='10'/>",
				"<method id='732' holder='729' name='leaf1' return='635' arguments='635' flags='2' bytes='4' compile_id='78' compiler='C2' iicount='10013'/>",
				"<call method='732' count='11725' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='732' uses='11725' stamp='11.373'>",
				"<uncommon_trap bci='10' reason='null_check' action='maybe_recompile'/>",
				"<parse_done nodes='145' live='140' memory='42224' stamp='11.373'/>",
				"</parse>",
				"<bc code='183' bci='16'/>",
				"<method id='733' holder='729' name='leaf2' return='635' arguments='635' flags='2' bytes='6' compile_id='79' compiler='C2' iicount='10013'/>",
				"<call method='733' count='11725' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='733' uses='11725' stamp='11.373'>",
				"<parse_done nodes='163' live='157' memory='45040' stamp='11.373'/>",
				"</parse>",
				"<bc code='183' bci='22'/>",
				"<method id='734' holder='729' name='leaf3' return='635' arguments='635' flags='2' bytes='6' compile_id='80' compiler='C2' iicount='10013'/>",
				"<call method='734' count='11725' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='734' uses='11725' stamp='11.373'>",
				"<parse_done nodes='180' live='173' memory='47760' stamp='11.374'/>",
				"</parse>",
				"<bc code='183' bci='28'/>",
				"<method id='735' holder='729' name='leaf4' return='635' arguments='635' flags='2' bytes='6' compile_id='81' compiler='C2' iicount='10026'/>",
				"<call method='735' count='11724' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='735' uses='11724' stamp='11.374'>",
				"<parse_done nodes='198' live='190' memory='50896' stamp='11.374'/>",
				"</parse>",
				"<bc code='155' bci='40'/>",
				"<branch target_bci='8' taken='11724' not_taken='0' cnt='11724' prob='always'/>",
				"<bc code='183' bci='52'/>",
				"<klass id='646' name='java/lang/String' flags='17'/>",
				"<klass id='704' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='738' holder='704' name='&lt;init&gt;' return='636' arguments='646' flags='1' bytes='18' iicount='9'/>",
				"<call method='738' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='call site not reached'/>",
				"<direct_call bci='52'/>",
				"<bc code='182' bci='56'/>",
				"<method id='739' holder='704' name='append' return='704' arguments='635' flags='1' bytes='8' iicount='9'/>",
				"<call method='739' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='56'/>",
				"<bc code='182' bci='59'/>",
				"<method id='740' holder='704' name='toString' return='646' flags='1' bytes='17' iicount='90'/>",
				"<call method='740' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='59'/>",
				"<uncommon_trap bci='59' reason='null_check' action='maybe_recompile'/>",
				"<bc code='182' bci='62'/>",
				"<klass id='736' name='java/io/PrintStream' flags='1'/>",
				"<method id='741' holder='736' name='println' return='636' arguments='646' flags='1' bytes='24' iicount='9'/>",
				"<dependency type='unique_concrete_method' ctxk='736' x='741'/>",
				"<call method='741' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='62'/>",
				"<uncommon_trap bci='62' reason='null_check' action='maybe_recompile'/>",
				"<parse_done nodes='337' live='326' memory='78696' stamp='11.375'/>",
				"</parse>",
				"<phase_done name='parse' nodes='340' live='190' stamp='11.376'/>",
				"</phase>",
				"<phase name='optimizer' nodes='340' live='190' stamp='11.376'>",
				"<phase name='idealLoop' nodes='345' live='181' stamp='11.376'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='347' live='181' stamp='11.376'/>",
				"</phase>",
				"<phase name='escapeAnalysis' nodes='347' live='181' stamp='11.376'>",
				"<phase name='connectionGraph' nodes='348' live='182' stamp='11.376'>",
				"<phase_done name='connectionGraph' nodes='348' live='182' stamp='11.378'/>",
				"</phase>",
				"<phase_done name='escapeAnalysis' nodes='348' live='182' stamp='11.378'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='348' live='182' stamp='11.378'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='353' live='179' stamp='11.379'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='353' live='179' stamp='11.379'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='353' live='179' stamp='11.379'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='353' live='179' stamp='11.379'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='353' live='179' stamp='11.379'/>",
				"</phase>",
				"<phase name='ccp' nodes='353' live='179' stamp='11.380'>",
				"<phase_done name='ccp' nodes='353' live='179' stamp='11.380'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='354' live='177' stamp='11.380'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='378' live='171' stamp='11.380'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='378' live='171' stamp='11.380'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='384' live='155' stamp='11.381'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='384' live='155' stamp='11.381'>",
				"<loop_tree>",
				"<loop idx='345' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='390' live='155' stamp='11.381'/>",
				"</phase>",
				"<phase_done name='optimizer' nodes='456' live='193' stamp='11.382'/>",
				"</phase>",
				"<phase name='matcher' nodes='456' live='193' stamp='11.382'>",
				"<phase_done name='matcher' nodes='169' live='169' stamp='11.383'/>",
				"</phase>",
				"<phase name='regalloc' nodes='213' live='213' stamp='11.383'>",
				"<regalloc attempts='1' success='1'/>",
				"<phase_done name='regalloc' nodes='250' live='245' stamp='11.386'/>",
				"</phase>",
				"<phase name='output' nodes='252' live='247' stamp='11.387'>",
				"<phase_done name='output' nodes='272' live='259' stamp='11.387'/>",
				"</phase>",
				"<dependency type='leaf_type' ctxk='729'/>",
				"<dependency type='unique_concrete_method' ctxk='736' x='741'/>",
				"<code_cache total_blobs='262' nmethods='82' adapters='134' free_code_cache='49820416' largest_free_block='49797376'/>",
				"<task_done success='1' nmsize='528' count='10000' backedge_count='5245' inlined_bytes='22' stamp='11.387'/>",
				"</task>"
		};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: goto            35   ",
				"8: aload_0         ",
				"9: lload_3         ",
				"10: invokespecial   #225 // Method leaf1:(J)J",
				"13: lstore_3        ",
				"14: aload_0         ",
				"15: lload_3         ",
				"16: invokespecial   #228 // Method leaf2:(J)J",
				"19: lstore_3        ",
				"20: aload_0         ",
				"21: lload_3         ",
				"22: invokespecial   #231 // Method leaf3:(J)J",
				"25: lstore_3        ",
				"26: aload_0         ",
				"27: lload_3         ",
				"28: invokespecial   #234 // Method leaf4:(J)J",
				"31: lstore_3        ",
				"32: iinc            5, 1 ",
				"35: iload           5    ",
				"37: i2l             ",
				"38: lload_1         ",
				"39: lcmp            ",
				"40: iflt            8    ",
				"43: getstatic       #52  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"46: new             #58  // class java/lang/StringBuilder",
				"49: dup             ",
				"50: ldc             #237 // String testLeaf:",
				"52: invokespecial   #62  // Method java/lang/StringBuilder.\"<init>\":(Ljava/lang/String;)V",
				"55: lload_3         ",
				"56: invokevirtual   #65  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"59: invokevirtual   #69  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"62: invokevirtual   #73  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"65: return          "
		};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testLeaf", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C2, logLines, bytecodeLines);

		assertEquals(9, result.size());

		checkLine(result, 10, "inline (hot)", Color.GREEN);
		checkLine(result, 16, "inline (hot)", Color.GREEN);
		checkLine(result, 22, "inline (hot)", Color.GREEN);
		checkLine(result, 28, "inline (hot)", Color.GREEN);
		checkLine(result, 40, "always", Color.BLUE);
		checkLine(result, 52, "not reached", Color.RED);
		checkLine(result, 56, "MinInliningThreshold", Color.RED);
		checkLine(result, 59, "MinInliningThreshold", Color.RED);
		checkLine(result, 62, "MinInliningThreshold", Color.RED);
	}

	@Test
	public void testJava7NonTieredChain()
	{
		String[] logLines = new String[]{
				"<task compile_id='73' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testCallChain (J)V' bytes='54' count='10000' backedge_count='5215' iicount='1' osr_bci='8' stamp='11.237'>",
				"<phase name='parse' nodes='3' live='3' stamp='11.237'>",
				"<type id='636' name='void'/>",
				"<type id='635' name='long'/>",
				"<klass id='729' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='730' holder='729' name='testCallChain' return='636' arguments='635' flags='2' bytes='54' iicount='1'/>",
				"<parse method='730' uses='1' osr_bci='8' stamp='11.238'>",
				"<dependency type='leaf_type' ctxk='729'/>",
				"<dependency type='leaf_type' ctxk='729'/>",
				"<uncommon_trap bci='8' reason='constraint' action='reinterpret'/>",
				"<uncommon_trap bci='8' reason='predicate' action='maybe_recompile'/>",
				"<uncommon_trap bci='8' reason='loop_limit_check' action='maybe_recompile'/>",
				"<bc code='183' bci='10'/>",
				"<method id='732' holder='729' name='chainA1' return='635' arguments='635' flags='2' bytes='8' compile_id='66' compiler='C2' iicount='10036'/>",
				"<call method='732' count='12009' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='732' uses='12009' stamp='11.239'>",
				"<uncommon_trap bci='10' reason='null_check' action='maybe_recompile'/>",
				"<bc code='183' bci='3'/>",
				"<method id='740' holder='729' name='chainA2' return='635' arguments='635' flags='2' bytes='10' compile_id='67' compiler='C2' iicount='10036'/>",
				"<call method='740' count='6737' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='740' uses='6737' stamp='11.239'>",
				"<bc code='183' bci='5'/>",
				"<method id='742' holder='729' name='chainA3' return='635' arguments='635' flags='2' bytes='10' compile_id='68' compiler='C2' iicount='10036'/>",
				"<call method='742' count='6737' prof_factor='0.671283' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='742' uses='4522' stamp='11.239'>",
				"<bc code='183' bci='5'/>",
				"<method id='744' holder='729' name='chainA4' return='635' arguments='635' flags='2' bytes='7' compile_id='69' compiler='C2' iicount='10036'/>",
				"<call method='744' count='6737' prof_factor='0.450578' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='744' uses='3036' stamp='11.239'>",
				"<bc code='183' bci='3'/>",
				"<type id='634' name='int'/>",
				"<method id='746' holder='729' name='bigMethod' return='635' arguments='635 634' flags='2' bytes='350' compile_id='16' compiler='C2' iicount='11219'/>",
				"<call method='746' count='6737' prof_factor='0.302511' inline='1'/>",
				"<inline_fail reason='hot method too big'/>",
				"<direct_call bci='3'/>",
				"<parse_done nodes='191' live='186' memory='50504' stamp='11.240'/>",
				"</parse>",
				"<parse_done nodes='194' live='188' memory='51680' stamp='11.240'/>",
				"</parse>",
				"<parse_done nodes='198' live='191' memory='53080' stamp='11.240'/>",
				"</parse>",
				"<parse_done nodes='202' live='194' memory='55040' stamp='11.240'/>",
				"</parse>",
				"<bc code='183' bci='16'/>",
				"<method id='733' holder='729' name='chainB1' return='635' arguments='635' flags='2' bytes='8' compile_id='70' compiler='C2' iicount='11154'/>",
				"<call method='733' count='12008' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='733' uses='12008' stamp='11.240'>",
				"<bc code='183' bci='2'/>",
				"<method id='748' holder='729' name='chainB2' return='635' arguments='635' flags='2' bytes='10' compile_id='71' compiler='C2' iicount='11154'/>",
				"<call method='748' count='7855' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='748' uses='7855' stamp='11.240'>",
				"<bc code='183' bci='2'/>",
				"<method id='750' holder='729' name='chainB3' return='635' arguments='635' flags='2' bytes='6' compile_id='72' compiler='C2' iicount='11154'/>",
				"<call method='750' count='7855' prof_factor='0.704232' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='750' uses='5532' stamp='11.240'>",
				"<parse_done nodes='243' live='234' memory='62248' stamp='11.240'/>",
				"</parse>",
				"<parse_done nodes='246' live='236' memory='62840' stamp='11.240'/>",
				"</parse>",
				"<parse_done nodes='249' live='238' memory='63336' stamp='11.240'/>",
				"</parse>",
				"<bc code='155' bci='28'/>",
				"<branch target_bci='8' taken='12008' not_taken='0' cnt='12008' prob='always'/>",
				"<bc code='183' bci='40'/>",
				"<klass id='646' name='java/lang/String' flags='17'/>",
				"<klass id='704' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='736' holder='704' name='&lt;init&gt;' return='636' arguments='646' flags='1' bytes='18' iicount='7'/>",
				"<call method='736' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='call site not reached'/>",
				"<direct_call bci='40'/>",
				"<bc code='182' bci='44'/>",
				"<method id='737' holder='704' name='append' return='704' arguments='635' flags='1' bytes='8' iicount='7'/>",
				"<call method='737' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='44'/>",
				"<bc code='182' bci='47'/>",
				"<method id='738' holder='704' name='toString' return='646' flags='1' bytes='17' iicount='88'/>",
				"<call method='738' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='47'/>",
				"<uncommon_trap bci='47' reason='null_check' action='maybe_recompile'/>",
				"<bc code='182' bci='50'/>",
				"<klass id='734' name='java/io/PrintStream' flags='1'/>",
				"<method id='739' holder='734' name='println' return='636' arguments='646' flags='1' bytes='24' iicount='7'/>",
				"<dependency type='unique_concrete_method' ctxk='734' x='739'/>",
				"<call method='739' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='50'/>",
				"<uncommon_trap bci='50' reason='null_check' action='maybe_recompile'/>",
				"<parse_done nodes='386' live='372' memory='92680' stamp='11.242'/>",
				"</parse>",
				"<phase_done name='parse' nodes='389' live='200' stamp='11.242'/>",
				"</phase>",
				"<phase name='optimizer' nodes='389' live='200' stamp='11.242'>",
				"<phase name='idealLoop' nodes='394' live='194' stamp='11.243'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='396' live='194' stamp='11.243'/>",
				"</phase>",
				"<phase name='escapeAnalysis' nodes='396' live='194' stamp='11.243'>",
				"<phase name='connectionGraph' nodes='397' live='195' stamp='11.243'>",
				"<phase_done name='connectionGraph' nodes='397' live='195' stamp='11.245'/>",
				"</phase>",
				"<phase_done name='escapeAnalysis' nodes='397' live='195' stamp='11.245'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='397' live='195' stamp='11.245'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='402' live='192' stamp='11.246'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='402' live='192' stamp='11.246'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='402' live='192' stamp='11.246'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='402' live='192' stamp='11.246'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='402' live='192' stamp='11.246'/>",
				"</phase>",
				"<phase name='ccp' nodes='402' live='192' stamp='11.247'>",
				"<phase_done name='ccp' nodes='402' live='192' stamp='11.247'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='403' live='189' stamp='11.247'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='421' live='183' stamp='11.248'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='421' live='183' stamp='11.248'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='421' live='167' stamp='11.248'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='421' live='167' stamp='11.248'>",
				"<loop_tree>",
				"<loop idx='394' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='421' live='167' stamp='11.249'/>",
				"</phase>",
				"<phase_done name='optimizer' nodes='484' live='202' stamp='11.249'/>",
				"</phase>",
				"<phase name='matcher' nodes='484' live='202' stamp='11.249'>",
				"<phase_done name='matcher' nodes='181' live='181' stamp='11.250'/>",
				"</phase>",
				"<phase name='regalloc' nodes='229' live='229' stamp='11.251'>",
				"<regalloc attempts='1' success='1'/>",
				"<phase_done name='regalloc' nodes='279' live='266' stamp='11.254'/>",
				"</phase>",
				"<phase name='output' nodes='281' live='268' stamp='11.254'>",
				"<phase_done name='output' nodes='308' live='285' stamp='11.255'/>",
				"</phase>",
				"<dependency type='leaf_type' ctxk='729'/>",
				"<dependency type='unique_concrete_method' ctxk='734' x='739'/>",
				"<code_cache total_blobs='253' nmethods='73' adapters='134' free_code_cache='49827328' largest_free_block='49803328'/>",
				"<task_done success='1' nmsize='576' count='10000' backedge_count='5296' inlined_bytes='59' stamp='11.256'/>",
				"</task>"
		};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: goto            23   ",
				"8: aload_0         ",
				"9: lload_3         ",
				"10: invokespecial   #190 // Method chainA1:(J)J",
				"13: lstore_3        ",
				"14: aload_0         ",
				"15: lload_3         ",
				"16: invokespecial   #194 // Method chainB1:(J)J",
				"19: lstore_3        ",
				"20: iinc            5, 1 ",
				"23: iload           5    ",
				"25: i2l             ",
				"26: lload_1         ",
				"27: lcmp            ",
				"28: iflt            8    ",
				"31: getstatic       #52  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"34: new             #58  // class java/lang/StringBuilder",
				"37: dup             ",
				"38: ldc             #197 // String testCallChain:",
				"40: invokespecial   #62  // Method java/lang/StringBuilder.\"<init>\":(Ljava/lang/String;)V",
				"43: lload_3         ",
				"44: invokevirtual   #65  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"47: invokevirtual   #69  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"50: invokevirtual   #73  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"53: return          "
		};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testCallChain", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C2, logLines, bytecodeLines);

		assertEquals(7, result.size());

		checkLine(result, 10, "inline (hot)", Color.GREEN);
		checkLine(result, 16, "inline (hot)", Color.GREEN);
		checkLine(result, 28, "always", Color.BLUE);
		checkLine(result, 40, "not reached", Color.RED);
		checkLine(result, 44, "MinInliningThreshold", Color.RED);
		checkLine(result, 47, "MinInliningThreshold", Color.RED);
		checkLine(result, 50, "MinInliningThreshold", Color.RED);
	}

	@Test
	public void testJava7TieredLeaf()
	{
		String[] logLines = new String[]{
				"<task compile_id='153' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testLeaf (J)V' bytes='66' count='1' backedge_count='60509' iicount='1' osr_bci='8' level='3' stamp='12.700'>",
				"<phase name='buildIR' stamp='12.700'>",
				"<type id='636' name='void'/>",
				"<type id='635' name='long'/>",
				"<klass id='729' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='730' holder='729' name='testLeaf' return='636' arguments='635' flags='2' bytes='66' iicount='1'/>",
				"<parse method='730'  stamp='12.700'>",
				"<bc code='183' bci='52'/>",
				"<klass id='646' name='java/lang/String' flags='17'/>",
				"<klass id='704' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='735' holder='704' name='&lt;init&gt;' return='636' arguments='646' flags='1' bytes='18' iicount='9'/>",
				"<call method='735' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='2'/>",
				"<type id='634' name='int'/>",
				"<method id='737' holder='646' name='length' return='634' flags='1' bytes='6' compile_id='6' compiler='C1' level='3' iicount='541'/>",
				"<call method='737' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='8'/>",
				"<klass id='702' name='java/lang/AbstractStringBuilder' flags='1024'/>",
				"<method id='739' holder='702' name='&lt;init&gt;' return='636' arguments='634' flags='0' bytes='12' iicount='101'/>",
				"<call method='739' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='1'/>",
				"<klass id='645' name='java/lang/Object' flags='1'/>",
				"<method id='741' holder='645' name='&lt;init&gt;' return='636' flags='1' bytes='1' compile_id='46' compiler='C1' level='1' iicount='20694'/>",
				"<call method='741' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='13'/>",
				"<method id='743' holder='704' name='append' return='704' arguments='646' flags='1' bytes='8' iicount='163'/>",
				"<call method='743' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='745' holder='702' name='append' return='702' arguments='646' flags='1' bytes='48' iicount='187'/>",
				"<call method='745' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='56'/>",
				"<method id='747' holder='704' name='append' return='704' arguments='635' flags='1' bytes='8' iicount='9'/>",
				"<call method='747' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='749' holder='702' name='append' return='702' arguments='635' flags='1' bytes='70' iicount='9'/>",
				"<call method='749' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='59'/>",
				"<method id='751' holder='704' name='toString' return='646' flags='1' bytes='17' iicount='90'/>",
				"<call method='751' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='13'/>",
				"<klass id='720' name='[C' flags='1041'/>",
				"<method id='753' holder='646' name='&lt;init&gt;' return='636' arguments='720 634 634' flags='1' bytes='67' iicount='215'/>",
				"<call method='753' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='62'/>",
				"<klass id='732' name='java/io/PrintStream' flags='1'/>",
				"<method id='755' holder='732' name='println' return='636' arguments='646' flags='1' bytes='24' iicount='9'/>",
				"<call method='755' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='6'/>",
				"<method id='757' holder='732' name='print' return='636' arguments='646' flags='1' bytes='13' iicount='9'/>",
				"<call method='757' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='9'/>",
				"<method id='759' holder='732' name='write' return='636' arguments='646' flags='2' bytes='83' iicount='9'/>",
				"<call method='759' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='10'/>",
				"<method id='763' holder='732' name='newLine' return='636' flags='2' bytes='73' iicount='9'/>",
				"<call method='763' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='10'/>",
				"<method id='766' holder='729' name='leaf1' return='635' arguments='635' flags='2' bytes='4' compile_id='149' compiler='C1' level='1' iicount='1962'/>",
				"<call method='766' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='16'/>",
				"<method id='768' holder='729' name='leaf2' return='635' arguments='635' flags='2' bytes='6' compile_id='150' compiler='C1' level='1' iicount='2685'/>",
				"<call method='768' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='22'/>",
				"<method id='770' holder='729' name='leaf3' return='635' arguments='635' flags='2' bytes='6' compile_id='151' compiler='C1' level='1' iicount='9780'/>",
				"<call method='770' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='28'/>",
				"<method id='772' holder='729' name='leaf4' return='635' arguments='635' flags='2' bytes='6' compile_id='152' compiler='C1' level='1' iicount='11340'/>",
				"<call method='772' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<parse_done stamp='12.703'/>",
				"</parse>",
				"<phase name='optimizeIR' stamp='12.703'>",
				"<phase_done stamp='12.703'/>",
				"</phase>",
				"<phase_done stamp='12.703'/>",
				"</phase>",
				"<phase name='emit_lir' stamp='12.703'>",
				"<phase name='lirGeneration' stamp='12.703'>",
				"<phase_done stamp='12.704'/>",
				"</phase>",
				"<phase name='linearScan' stamp='12.704'>",
				"<phase_done stamp='12.705'/>",
				"</phase>",
				"<phase_done stamp='12.705'/>",
				"</phase>",
				"<phase name='codeemit' stamp='12.705'>",
				"<phase_done stamp='12.706'/>",
				"</phase>",
				"<phase name='codeinstall' stamp='12.706'>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<phase_done stamp='12.706'/>",
				"</phase>",
				"<code_cache total_blobs='365' nmethods='153' adapters='134' free_code_cache='99240832' largest_free_block='99229888'/>",
				"<task_done success='1' nmsize='3560' count='1' backedge_count='70671' inlined_bytes='129' stamp='12.706'/>",
				"</task>"
		};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: goto            35   ",
				"8: aload_0         ",
				"9: lload_3         ",
				"10: invokespecial   #225 // Method leaf1:(J)J",
				"13: lstore_3        ",
				"14: aload_0         ",
				"15: lload_3         ",
				"16: invokespecial   #228 // Method leaf2:(J)J",
				"19: lstore_3        ",
				"20: aload_0         ",
				"21: lload_3         ",
				"22: invokespecial   #231 // Method leaf3:(J)J",
				"25: lstore_3        ",
				"26: aload_0         ",
				"27: lload_3         ",
				"28: invokespecial   #234 // Method leaf4:(J)J",
				"31: lstore_3        ",
				"32: iinc            5, 1 ",
				"35: iload           5    ",
				"37: i2l             ",
				"38: lload_1         ",
				"39: lcmp            ",
				"40: iflt            8    ",
				"43: getstatic       #52  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"46: new             #58  // class java/lang/StringBuilder",
				"49: dup             ",
				"50: ldc             #237 // String testLeaf:",
				"52: invokespecial   #62  // Method java/lang/StringBuilder.\"<init>\":(Ljava/lang/String;)V",
				"55: lload_3         ",
				"56: invokevirtual   #65  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"59: invokevirtual   #69  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"62: invokevirtual   #73  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"65: return          "
		};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testLeaf", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C1, logLines, bytecodeLines);

		assertEquals(8, result.size());

		int bcOffsetStringBuilderInit = 52;
		int bcOffsetMakeHotSpotLogLeaf1 = 10;
		int bcOffsetMakeHotSpotLogLeaf2 = 16;
		int bcOffsetMakeHotSpotLogLeaf3 = 22;
		int bcOffsetMakeHotSpotLogLeaf4 = 28;
		int bcOffsetStringBuilderAppend = 56;
		int bcOffsetStringBuilderToString = 59;
		int bcOffsetPrintStreamPrintln = 62;

		checkLine(result, bcOffsetStringBuilderInit, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetMakeHotSpotLogLeaf1, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetMakeHotSpotLogLeaf2, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetMakeHotSpotLogLeaf3, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetMakeHotSpotLogLeaf4, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetStringBuilderAppend, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetStringBuilderToString, "Inlined: Yes", Color.GREEN);
		checkLine(result, bcOffsetPrintStreamPrintln, "Inlined: Yes", Color.GREEN);
	}

	@Test
	public void testJava7TieredChain()
	{
		String[] logLines = new String[]{
				"<task compile_id='133' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testCallChain (J)V' bytes='54' count='1' backedge_count='60635' iicount='1' osr_bci='8' level='3' stamp='12.538'>",
				"<phase name='buildIR' stamp='12.538'>",
				"<type id='636' name='void'/>",
				"<type id='635' name='long'/>",
				"<klass id='729' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='730' holder='729' name='testCallChain' return='636' arguments='635' flags='2' bytes='54' iicount='1'/>",
				"<parse method='730'  stamp='12.538'>",
				"<bc code='183' bci='40'/>",
				"<klass id='646' name='java/lang/String' flags='17'/>",
				"<klass id='704' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='735' holder='704' name='&lt;init&gt;' return='636' arguments='646' flags='1' bytes='18' iicount='7'/>",
				"<call method='735' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='2'/>",
				"<type id='634' name='int'/>",
				"<method id='737' holder='646' name='length' return='634' flags='1' bytes='6' compile_id='6' compiler='C1' level='3' iicount='533'/>",
				"<call method='737' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='8'/>",
				"<klass id='702' name='java/lang/AbstractStringBuilder' flags='1024'/>",
				"<method id='739' holder='702' name='&lt;init&gt;' return='636' arguments='634' flags='0' bytes='12' iicount='99'/>",
				"<call method='739' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='1'/>",
				"<klass id='645' name='java/lang/Object' flags='1'/>",
				"<method id='741' holder='645' name='&lt;init&gt;' return='636' flags='1' bytes='1' compile_id='46' compiler='C1' level='1' iicount='20694'/>",
				"<call method='741' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='13'/>",
				"<method id='743' holder='704' name='append' return='704' arguments='646' flags='1' bytes='8' iicount='161'/>",
				"<call method='743' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='745' holder='702' name='append' return='702' arguments='646' flags='1' bytes='48' iicount='185'/>",
				"<call method='745' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='44'/>",
				"<method id='747' holder='704' name='append' return='704' arguments='635' flags='1' bytes='8' iicount='7'/>",
				"<call method='747' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='749' holder='702' name='append' return='702' arguments='635' flags='1' bytes='70' iicount='7'/>",
				"<call method='749' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='47'/>",
				"<method id='751' holder='704' name='toString' return='646' flags='1' bytes='17' iicount='88'/>",
				"<call method='751' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='13'/>",
				"<klass id='720' name='[C' flags='1041'/>",
				"<method id='753' holder='646' name='&lt;init&gt;' return='636' arguments='720 634 634' flags='1' bytes='67' iicount='213'/>",
				"<call method='753' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='50'/>",
				"<klass id='732' name='java/io/PrintStream' flags='1'/>",
				"<method id='755' holder='732' name='println' return='636' arguments='646' flags='1' bytes='24' iicount='7'/>",
				"<call method='755' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='6'/>",
				"<method id='757' holder='732' name='print' return='636' arguments='646' flags='1' bytes='13' iicount='7'/>",
				"<call method='757' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='9'/>",
				"<method id='759' holder='732' name='write' return='636' arguments='646' flags='2' bytes='83' iicount='7'/>",
				"<call method='759' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='10'/>",
				"<method id='763' holder='732' name='newLine' return='636' flags='2' bytes='73' iicount='7'/>",
				"<call method='763' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='10'/>",
				"<method id='766' holder='729' name='chainA1' return='635' arguments='635' flags='2' bytes='8' compile_id='131' compiler='C2' level='4' iicount='11516'/>",
				"<call method='766' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='3'/>",
				"<method id='768' holder='729' name='chainA2' return='635' arguments='635' flags='2' bytes='10' iicount='11516'/>",
				"<call method='768' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='5'/>",
				"<method id='770' holder='729' name='chainA3' return='635' arguments='635' flags='2' bytes='10' iicount='11516'/>",
				"<call method='770' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='5'/>",
				"<method id='772' holder='729' name='chainA4' return='635' arguments='635' flags='2' bytes='7' iicount='11516'/>",
				"<call method='772' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='3'/>",
				"<method id='774' holder='729' name='bigMethod' return='635' arguments='635 634' flags='2' bytes='350' compile_id='41' compiler='C2' level='4' iicount='6537'/>",
				"<call method='774' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='16'/>",
				"<method id='776' holder='729' name='chainB1' return='635' arguments='635' flags='2' bytes='8' compile_id='132' compiler='C2' level='4' iicount='16492'/>",
				"<call method='776' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='778' holder='729' name='chainB2' return='635' arguments='635' flags='2' bytes='10' iicount='16492'/>",
				"<call method='778' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='780' holder='729' name='chainB3' return='635' arguments='635' flags='2' bytes='6' iicount='16492'/>",
				"<call method='780' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<parse_done stamp='12.542'/>",
				"</parse>",
				"<phase name='optimizeIR' stamp='12.542'>",
				"<phase_done stamp='12.542'/>",
				"</phase>",
				"<phase_done stamp='12.542'/>",
				"</phase>",
				"<phase name='emit_lir' stamp='12.542'>",
				"<phase name='lirGeneration' stamp='12.542'>",
				"<phase_done stamp='12.543'/>",
				"</phase>",
				"<phase name='linearScan' stamp='12.543'>",
				"<phase_done stamp='12.544'/>",
				"</phase>",
				"<phase_done stamp='12.544'/>",
				"</phase>",
				"<phase name='codeemit' stamp='12.544'>",
				"<phase_done stamp='12.545'/>",
				"</phase>",
				"<phase name='codeinstall' stamp='12.545'>",
				"<dependency type='leaf_type' ctxk='732'/>",
				"<phase_done stamp='12.545'/>",
				"</phase>",
				"<code_cache total_blobs='345' nmethods='133' adapters='134' free_code_cache='99281280' largest_free_block='99255360'/>",
				"<task_done success='1' nmsize='3960' count='1' backedge_count='82045' inlined_bytes='166' stamp='12.545'/>",
				"</task>"
		};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: goto            23   ",
				"8: aload_0         ",
				"9: lload_3         ",
				"10: invokespecial   #190 // Method chainA1:(J)J",
				"13: lstore_3        ",
				"14: aload_0         ",
				"15: lload_3         ",
				"16: invokespecial   #194 // Method chainB1:(J)J",
				"19: lstore_3        ",
				"20: iinc            5, 1 ",
				"23: iload           5    ",
				"25: i2l             ",
				"26: lload_1         ",
				"27: lcmp            ",
				"28: iflt            8    ",
				"31: getstatic       #52  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"34: new             #58  // class java/lang/StringBuilder",
				"37: dup             ",
				"38: ldc             #197 // String testCallChain:",
				"40: invokespecial   #62  // Method java/lang/StringBuilder.\"<init>\":(Ljava/lang/String;)V",
				"43: lload_3         ",
				"44: invokevirtual   #65  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"47: invokevirtual   #69  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"50: invokevirtual   #73  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"53: return          "
		};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testCallChain", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C1, logLines, bytecodeLines);

		assertEquals(6, result.size());

		checkLine(result, 10, "Inlined: Yes", Color.GREEN);
		checkLine(result, 16, "Inlined: Yes", Color.GREEN);
		checkLine(result, 40, "Inlined: Yes", Color.GREEN);
		checkLine(result, 44, "Inlined: Yes", Color.GREEN);
		checkLine(result, 47, "Inlined: Yes", Color.GREEN);
		checkLine(result, 50, "Inlined: Yes", Color.GREEN);
	}

	@Test
	public void testJava8NonTieredLeaf()
	{
		String[] logLines = new String[]{
				"<task compile_id='78' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testLeaf (J)V' bytes='69' count='10000' backedge_count='5059' iicount='1' osr_bci='5' stamp='11.551'>",
				"<phase name='parse' nodes='3' live='3' stamp='11.551'>",
				"<type id='680' name='void'/>",
				"<type id='679' name='long'/>",
				"<klass id='776' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='777' holder='776' name='testLeaf' return='680' arguments='679' flags='2' bytes='69' iicount='1'/>",
				"<parse method='777' uses='1' osr_bci='5' stamp='11.552'>",
				"<dependency type='leaf_type' ctxk='776'/>",
				"<dependency type='leaf_type' ctxk='776'/>",
				"<uncommon_trap bci='5' reason='constraint' action='reinterpret'/>",
				"<uncommon_trap bci='5' reason='predicate' action='maybe_recompile'/>",
				"<uncommon_trap bci='5' reason='loop_limit_check' action='maybe_recompile'/>",
				"<bc code='156' bci='10'/>",
				"<branch target_bci='43' taken='0' not_taken='11547' cnt='11547' prob='never'/>",
				"<bc code='183' bci='15'/>",
				"<method id='786' holder='776' name='leaf1' return='679' arguments='679' flags='2' bytes='4' compile_id='74' compiler='C2' iicount='10805'/>",
				"<call method='786' count='11547' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='786' uses='11547' stamp='11.553'>",
				"<uncommon_trap bci='15' reason='null_check' action='maybe_recompile'/>",
				"<parse_done nodes='155' live='150' memory='43768' stamp='11.553'/>",
				"</parse>",
				"<bc code='183' bci='21'/>",
				"<method id='787' holder='776' name='leaf2' return='679' arguments='679' flags='2' bytes='6' compile_id='75' compiler='C2' iicount='11803'/>",
				"<call method='787' count='11546' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='787' uses='11546' stamp='11.553'>",
				"<parse_done nodes='173' live='167' memory='46304' stamp='11.553'/>",
				"</parse>",
				"<bc code='183' bci='27'/>",
				"<method id='788' holder='776' name='leaf3' return='679' arguments='679' flags='2' bytes='6' compile_id='76' compiler='C2' iicount='13042'/>",
				"<call method='788' count='11546' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='788' uses='11546' stamp='11.553'>",
				"<parse_done nodes='190' live='183' memory='49576' stamp='11.555'/>",
				"</parse>",
				"<bc code='183' bci='33'/>",
				"<method id='789' holder='776' name='leaf4' return='679' arguments='679' flags='2' bytes='6' compile_id='77' compiler='C2' iicount='15225'/>",
				"<call method='789' count='11546' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='789' uses='11546' stamp='11.555'>",
				"<parse_done nodes='208' live='200' memory='52048' stamp='11.555'/>",
				"</parse>",
				"<bc code='183' bci='50'/>",
				"<klass id='749' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='780' holder='749' name='&lt;init&gt;' return='680' flags='1' bytes='7' iicount='114'/>",
				"<call method='780' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='call site not reached'/>",
				"<direct_call bci='50'/>",
				"<bc code='182' bci='55'/>",
				"<klass id='686' name='java/lang/String' flags='17'/>",
				"<method id='782' holder='749' name='append' return='749' arguments='686' flags='1' bytes='8' iicount='209'/>",
				"<call method='782' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='55'/>",
				"<bc code='182' bci='59'/>",
				"<method id='783' holder='749' name='append' return='749' arguments='679' flags='1' bytes='8' iicount='9'/>",
				"<call method='783' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='59'/>",
				"<uncommon_trap bci='59' reason='null_check' action='maybe_recompile'/>",
				"<bc code='182' bci='62'/>",
				"<method id='784' holder='749' name='toString' return='686' flags='1' bytes='17' iicount='113'/>",
				"<call method='784' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='62'/>",
				"<uncommon_trap bci='62' reason='null_check' action='maybe_recompile'/>",
				"<bc code='182' bci='65'/>",
				"<klass id='779' name='java/io/PrintStream' flags='1'/>",
				"<method id='785' holder='779' name='println' return='680' arguments='686' flags='1' bytes='24' iicount='9'/>",
				"<dependency type='unique_concrete_method' ctxk='779' x='785'/>",
				"<call method='785' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='65'/>",
				"<uncommon_trap bci='65' reason='null_check' action='maybe_recompile'/>",
				"<parse_done nodes='365' live='353' memory='83024' stamp='11.557'/>",
				"</parse>",
				"<phase_done name='parse' nodes='368' live='210' stamp='11.557'/>",
				"</phase>",
				"<phase name='optimizer' nodes='368' live='210' stamp='11.557'>",
				"<phase name='idealLoop' nodes='373' live='201' stamp='11.557'>",
				"<loop_tree>",
				"<loop idx='373' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='374' live='201' stamp='11.558'/>",
				"</phase>",
				"<phase name='escapeAnalysis' nodes='374' live='201' stamp='11.558'>",
				"<phase name='connectionGraph' nodes='375' live='202' stamp='11.558'>",
				"<klass id='747' name='java/lang/AbstractStringBuilder' flags='1024'/>",
				"<type id='678' name='int'/>",
				"<method id='808' holder='747' name='expandCapacity' return='680' arguments='678' flags='0' bytes='50' iicount='157'/>",
				"<dependency type='unique_concrete_method' ctxk='747' x='808'/>",
				"<phase_done name='connectionGraph' nodes='375' live='202' stamp='11.560'/>",
				"</phase>",
				"<phase_done name='escapeAnalysis' nodes='375' live='202' stamp='11.560'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='375' live='202' stamp='11.560'>",
				"<loop_tree>",
				"<loop idx='373' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='399' live='213' stamp='11.561'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='399' live='213' stamp='11.561'>",
				"<loop_tree>",
				"<loop idx='373' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='399' live='194' stamp='11.561'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='399' live='194' stamp='11.561'>",
				"<loop_tree>",
				"<loop idx='373' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='399' live='194' stamp='11.562'/>",
				"</phase>",
				"<phase name='ccp' nodes='399' live='194' stamp='11.562'>",
				"<phase_done name='ccp' nodes='399' live='194' stamp='11.562'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='400' live='191' stamp='11.562'>",
				"<loop_tree>",
				"<loop idx='373' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='400' live='191' stamp='11.563'/>",
				"</phase>",
				"<phase_done name='optimizer' nodes='468' live='229' stamp='11.563'/>",
				"</phase>",
				"<phase name='matcher' nodes='468' live='229' stamp='11.563'>",
				"<phase_done name='matcher' nodes='210' live='210' stamp='11.564'/>",
				"</phase>",
				"<phase name='regalloc' nodes='268' live='268' stamp='11.565'>",
				"<regalloc attempts='1' success='1'/>",
				"<phase_done name='regalloc' nodes='302' live='300' stamp='11.569'/>",
				"</phase>",
				"<phase name='output' nodes='304' live='302' stamp='11.569'>",
				"<phase_done name='output' nodes='331' live='319' stamp='11.570'/>",
				"</phase>",
				"<dependency type='leaf_type' ctxk='776'/>",
				"<dependency type='unique_concrete_method' ctxk='779' x='785'/>",
				"<dependency type='unique_concrete_method' ctxk='747' x='808'/>",
				"<code_cache total_blobs='268' nmethods='78' adapters='142' free_code_cache='49725632'/>",
				"<task_done success='1' nmsize='608' count='10000' backedge_count='5598' inlined_bytes='22' stamp='11.570'/>",
				"</task>"
			};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: iload           5    ",
				"7: i2l             ",
				"8: lload_1         ",
				"9: lcmp            ",
				"10: ifge            43   ",
				"13: aload_0         ",
				"14: lload_3         ",
				"15: invokespecial   #70  // Method leaf1:(J)J",
				"18: lstore_3        ",
				"19: aload_0         ",
				"20: lload_3         ",
				"21: invokespecial   #71  // Method leaf2:(J)J",
				"24: lstore_3        ",
				"25: aload_0         ",
				"26: lload_3         ",
				"27: invokespecial   #72  // Method leaf3:(J)J",
				"30: lstore_3        ",
				"31: aload_0         ",
				"32: lload_3         ",
				"33: invokespecial   #73  // Method leaf4:(J)J",
				"36: lstore_3        ",
				"37: iinc            5, 1 ",
				"40: goto            5    ",
				"43: getstatic       #13  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"46: new             #14  // class java/lang/StringBuilder",
				"49: dup             ",
				"50: invokespecial   #15  // Method java/lang/StringBuilder.\"<init>\":()V",
				"53: ldc             #74  // String testLeaf:",
				"55: invokevirtual   #17  // Method java/lang/StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;",
				"58: lload_3         ",
				"59: invokevirtual   #18  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"62: invokevirtual   #19  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"65: invokevirtual   #20  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"68: return          "
				};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testLeaf", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C2, logLines, bytecodeLines);

		assertEquals(10, result.size());

		checkLine(result, 10, "never", Color.BLUE);
		checkLine(result, 15, "inline (hot)", Color.GREEN);
		checkLine(result, 21, "inline (hot)", Color.GREEN);
		checkLine(result, 27, "inline (hot)", Color.GREEN);
		checkLine(result, 33, "inline (hot)", Color.GREEN);
		checkLine(result, 50, "not reached", Color.RED);
		checkLine(result, 55, "MinInliningThreshold", Color.RED);
		checkLine(result, 59, "MinInliningThreshold", Color.RED);
		checkLine(result, 62, "MinInliningThreshold", Color.RED);
		checkLine(result, 65, "MinInliningThreshold", Color.RED);
	}

	/*
	@Test
	public void testJava8NonTieredChain()
	{
		String[] logLines = new String[]{
				"<task compile_id='73' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testCallChain2 (J)V' bytes='57' count='10000' backedge_count='5171' iicount='1' osr_bci='5' stamp='11.507'>",
				"<phase name='parse' nodes='3' live='3' stamp='11.507'>",
				"<type id='680' name='void'/>",
				"<type id='679' name='long'/>",
				"<klass id='776' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='777' holder='776' name='testCallChain2' return='680' arguments='679' flags='2' bytes='57' iicount='1'/>",
				"<parse method='777' uses='1' osr_bci='5' stamp='11.508'>",
				"<dependency type='leaf_type' ctxk='776'/>",
				"<dependency type='leaf_type' ctxk='776'/>",
				"<uncommon_trap bci='5' reason='constraint' action='reinterpret'/>",
				"<uncommon_trap bci='5' reason='predicate' action='maybe_recompile'/>",
				"<uncommon_trap bci='5' reason='loop_limit_check' action='maybe_recompile'/>",
				"<bc code='156' bci='10'/>",
				"<branch target_bci='31' taken='0' not_taken='14038' cnt='14038' prob='never'/>",
				"<bc code='183' bci='15'/>",
				"<method id='786' holder='776' name='chainC1' return='679' arguments='679' flags='2' bytes='14' compile_id='71' compiler='C2' iicount='12250'/>",
				"<call method='786' count='14038' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='786' uses='14038' stamp='11.509'>",
				"<uncommon_trap bci='15' reason='null_check' action='maybe_recompile'/>",
				"<bc code='183' bci='3'/>",
				"<method id='787' holder='776' name='chainC2' return='679' arguments='679' flags='2' bytes='6' compile_id='70' compiler='C2' iicount='11615'/>",
				"<call method='787' count='8951' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='787' uses='8951' stamp='11.509'>",
				"<parse_done nodes='165' live='160' memory='45488' stamp='11.509'/>",
				"</parse>",
				"<bc code='183' bci='10'/>",
				"<method id='788' holder='776' name='chainC3' return='679' arguments='679' flags='2' bytes='6' compile_id='72' compiler='C2' iicount='12250'/>",
				"<call method='788' count='8951' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='788' uses='8951' stamp='11.509'>",
				"<parse_done nodes='182' live='176' memory='48192' stamp='11.509'/>",
				"</parse>",
				"<parse_done nodes='183' live='176' memory='49104' stamp='11.509'/>",
				"</parse>",
				"<bc code='183' bci='21'/>",
				"<call method='787' count='14037' prof_factor='1' inline='1'/>",
				"<inline_success reason='inline (hot)'/>",
				"<parse method='787' uses='14037' stamp='11.509'>",
				"<parse_done nodes='200' live='192' memory='51352' stamp='11.509'/>",
				"</parse>",
				"<bc code='183' bci='38'/>",
				"<klass id='749' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='780' holder='749' name='&lt;init&gt;' return='680' flags='1' bytes='7' iicount='113'/>",
				"<call method='780' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='call site not reached'/>",
				"<direct_call bci='38'/>",
				"<bc code='182' bci='43'/>",
				"<klass id='686' name='java/lang/String' flags='17'/>",
				"<method id='782' holder='749' name='append' return='749' arguments='686' flags='1' bytes='8' iicount='208'/>",
				"<call method='782' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='43'/>",
				"<bc code='182' bci='47'/>",
				"<method id='783' holder='749' name='append' return='749' arguments='679' flags='1' bytes='8' iicount='8'/>",
				"<call method='783' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='47'/>",
				"<uncommon_trap bci='47' reason='null_check' action='maybe_recompile'/>",
				"<bc code='182' bci='50'/>",
				"<method id='784' holder='749' name='toString' return='686' flags='1' bytes='17' iicount='112'/>",
				"<call method='784' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='50'/>",
				"<uncommon_trap bci='50' reason='null_check' action='maybe_recompile'/>",
				"<bc code='182' bci='53'/>",
				"<klass id='779' name='java/io/PrintStream' flags='1'/>",
				"<method id='785' holder='779' name='println' return='680' arguments='686' flags='1' bytes='24' iicount='8'/>",
				"<dependency type='unique_concrete_method' ctxk='779' x='785'/>",
				"<call method='785' count='0' prof_factor='1' inline='1'/>",
				"<inline_fail reason='executed &lt; MinInliningThreshold times'/>",
				"<direct_call bci='53'/>",
				"<uncommon_trap bci='53' reason='null_check' action='maybe_recompile'/>",
				"<parse_done nodes='357' live='345' memory='81672' stamp='11.511'/>",
				"</parse>",
				"<phase_done name='parse' nodes='360' live='211' stamp='11.512'/>",
				"</phase>",
				"<phase name='optimizer' nodes='360' live='211' stamp='11.512'>",
				"<phase name='idealLoop' nodes='365' live='202' stamp='11.512'>",
				"<loop_tree>",
				"<loop idx='365' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='366' live='202' stamp='11.513'/>",
				"</phase>",
				"<phase name='escapeAnalysis' nodes='366' live='202' stamp='11.513'>",
				"<phase name='connectionGraph' nodes='367' live='203' stamp='11.513'>",
				"<klass id='747' name='java/lang/AbstractStringBuilder' flags='1024'/>",
				"<type id='678' name='int'/>",
				"<method id='806' holder='747' name='expandCapacity' return='680' arguments='678' flags='0' bytes='50' iicount='156'/>",
				"<dependency type='unique_concrete_method' ctxk='747' x='806'/>",
				"<phase_done name='connectionGraph' nodes='367' live='203' stamp='11.515'/>",
				"</phase>",
				"<phase_done name='escapeAnalysis' nodes='367' live='203' stamp='11.515'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='367' live='203' stamp='11.515'>",
				"<loop_tree>",
				"<loop idx='365' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='392' live='215' stamp='11.516'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='392' live='215' stamp='11.516'>",
				"<loop_tree>",
				"<loop idx='365' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='392' live='196' stamp='11.516'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='392' live='196' stamp='11.516'>",
				"<loop_tree>",
				"<loop idx='365' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='392' live='196' stamp='11.516'/>",
				"</phase>",
				"<phase name='ccp' nodes='392' live='196' stamp='11.517'>",
				"<phase_done name='ccp' nodes='392' live='196' stamp='11.517'/>",
				"</phase>",
				"<phase name='idealLoop' nodes='393' live='193' stamp='11.517'>",
				"<loop_tree>",
				"<loop idx='365' inner_loop='1' >",
				"</loop>",
				"</loop_tree>",
				"<phase_done name='idealLoop' nodes='393' live='193' stamp='11.517'/>",
				"</phase>",
				"<phase_done name='optimizer' nodes='461' live='231' stamp='11.518'/>",
				"</phase>",
				"<phase name='matcher' nodes='461' live='231' stamp='11.518'>",
				"<phase_done name='matcher' nodes='214' live='214' stamp='11.519'/>",
				"</phase>",
				"<phase name='regalloc' nodes='272' live='272' stamp='11.520'>",
				"<regalloc attempts='1' success='1'/>",
				"<phase_done name='regalloc' nodes='306' live='304' stamp='11.525'/>",
				"</phase>",
				"<phase name='output' nodes='308' live='306' stamp='11.525'>",
				"<phase_done name='output' nodes='337' live='325' stamp='11.526'/>",
				"</phase>",
				"<dependency type='leaf_type' ctxk='776'/>",
				"<dependency type='unique_concrete_method' ctxk='779' x='785'/>",
				"<dependency type='unique_concrete_method' ctxk='747' x='806'/>",
				"<code_cache total_blobs='263' nmethods='73' adapters='142' free_code_cache='49729600'/>",
				"<task_done success='1' nmsize='640' count='10000' backedge_count='5906' inlined_bytes='32' stamp='11.526'/>",
				"</task>"
		};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: iload           5    ",
				"7: i2l             ",
				"8: lload_1         ",
				"9: lcmp            ",
				"10: ifge            31   ",
				"13: aload_0         ",
				"14: lload_3         ",
				"15: invokespecial   #58  // Method chainA1:(J)J",
				"18: lstore_3        ",
				"19: aload_0         ",
				"20: lload_3         ",
				"21: invokespecial   #59  // Method chainB1:(J)J",
				"24: lstore_3        ",
				"25: iinc            5, 1 ",
				"28: goto            5    ",
				"31: getstatic       #13  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"34: new             #14  // class java/lang/StringBuilder",
				"37: dup             ",
				"38: invokespecial   #15  // Method java/lang/StringBuilder.\"<init>\":()V",
				"41: ldc             #60  // String testCallChain:",
				"43: invokevirtual   #17  // Method java/lang/StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;",
				"46: lload_3         ",
				"47: invokevirtual   #18  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"50: invokevirtual   #19  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"53: invokevirtual   #20  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"56: return          "
		};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testCallChain2", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C2, logLines, bytecodeLines);

		assertEquals(8, result.size());

		checkLine(result, 10, "never", Color.BLUE);
		checkLine(result, 15, "inline (hot)", Color.GREEN);
		checkLine(result, 21, "inline (hot)", Color.GREEN);
		checkLine(result, 38, "not reached", Color.RED);
		checkLine(result, 43, "MinInliningThreshold", Color.RED);
		checkLine(result, 47, "MinInliningThreshold", Color.RED);
		checkLine(result, 50, "MinInliningThreshold", Color.RED);
		checkLine(result, 53, "MinInliningThreshold", Color.RED);
	}
	*/

	@Test
	public void testJava8TieredLeaf()
	{
		String[] logLines = new String[]{
				"<task compile_id='153' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testLeaf (J)V' bytes='69' count='1' backedge_count='60592' iicount='1' osr_bci='5' level='3' stamp='12.193'>",
				"<phase name='buildIR' stamp='12.193'>",
				"<type id='680' name='void'/>",
				"<type id='679' name='long'/>",
				"<klass id='776' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='777' holder='776' name='testLeaf' return='680' arguments='679' flags='2' bytes='69' iicount='1'/>",
				"<parse method='777'  stamp='12.193'>",
				"<bc code='183' bci='15'/>",
				"<method id='779' holder='776' name='leaf1' return='679' arguments='679' flags='2' bytes='4' compile_id='149' compiler='C1' level='1' iicount='6137'/>",
				"<call method='779' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='21'/>",
				"<method id='781' holder='776' name='leaf2' return='679' arguments='679' flags='2' bytes='6' compile_id='150' compiler='C1' level='1' iicount='5327'/>",
				"<call method='781' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='27'/>",
				"<method id='783' holder='776' name='leaf3' return='679' arguments='679' flags='2' bytes='6' compile_id='151' compiler='C1' level='1' iicount='10055'/>",
				"<call method='783' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='33'/>",
				"<method id='785' holder='776' name='leaf4' return='679' arguments='679' flags='2' bytes='6' compile_id='152' compiler='C1' level='1' iicount='11585'/>",
				"<call method='785' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='50'/>",
				"<klass id='749' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='789' holder='749' name='&lt;init&gt;' return='680' flags='1' bytes='7' iicount='114'/>",
				"<call method='789' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='3'/>",
				"<type id='678' name='int'/>",
				"<klass id='747' name='java/lang/AbstractStringBuilder' flags='1024'/>",
				"<method id='791' holder='747' name='&lt;init&gt;' return='680' arguments='678' flags='0' bytes='12' iicount='127'/>",
				"<call method='791' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='1'/>",
				"<klass id='685' name='java/lang/Object' flags='1'/>",
				"<method id='793' holder='685' name='&lt;init&gt;' return='680' flags='1' bytes='1' compile_id='10' compiler='C1' level='1' iicount='447535'/>",
				"<call method='793' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='55'/>",
				"<klass id='686' name='java/lang/String' flags='17'/>",
				"<method id='796' holder='749' name='append' return='749' arguments='686' flags='1' bytes='8' iicount='209'/>",
				"<call method='796' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='798' holder='747' name='append' return='747' arguments='686' flags='1' bytes='50' iicount='242'/>",
				"<call method='798' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='59'/>",
				"<method id='800' holder='749' name='append' return='749' arguments='679' flags='1' bytes='8' iicount='9'/>",
				"<call method='800' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='802' holder='747' name='append' return='747' arguments='679' flags='1' bytes='70' iicount='9'/>",
				"<call method='802' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='62'/>",
				"<method id='804' holder='749' name='toString' return='686' flags='1' bytes='17' iicount='113'/>",
				"<call method='804' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='13'/>",
				"<klass id='765' name='[C' flags='1041'/>",
				"<method id='806' holder='686' name='&lt;init&gt;' return='680' arguments='765 678 678' flags='1' bytes='62' iicount='262'/>",
				"<call method='806' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='65'/>",
				"<klass id='787' name='java/io/PrintStream' flags='1'/>",
				"<method id='808' holder='787' name='println' return='680' arguments='686' flags='1' bytes='24' iicount='9'/>",
				"<call method='808' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='787'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='6'/>",
				"<method id='810' holder='787' name='print' return='680' arguments='686' flags='1' bytes='13' iicount='9'/>",
				"<call method='810' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='787'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='9'/>",
				"<method id='812' holder='787' name='write' return='680' arguments='686' flags='2' bytes='83' iicount='9'/>",
				"<call method='812' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='787'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='10'/>",
				"<method id='816' holder='787' name='newLine' return='680' flags='2' bytes='73' iicount='9'/>",
				"<call method='816' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='787'/>",
				"<inline_fail reason='callee is too large'/>",
				"<parse_done stamp='12.196'/>",
				"</parse>",
				"<phase name='optimize_blocks' stamp='12.196'>",
				"<phase_done name='optimize_blocks' stamp='12.197'/>",
				"</phase>",
				"<phase name='optimize_null_checks' stamp='12.197'>",
				"<phase_done name='optimize_null_checks' stamp='12.197'/>",
				"</phase>",
				"<phase_done name='buildIR' stamp='12.197'/>",
				"</phase>",
				"<phase name='emit_lir' stamp='12.197'>",
				"<phase name='lirGeneration' stamp='12.197'>",
				"<phase_done name='lirGeneration' stamp='12.197'/>",
				"</phase>",
				"<phase name='linearScan' stamp='12.197'>",
				"<phase_done name='linearScan' stamp='12.198'/>",
				"</phase>",
				"<phase_done name='emit_lir' stamp='12.198'/>",
				"</phase>",
				"<phase name='codeemit' stamp='12.198'>",
				"<phase_done name='codeemit' stamp='12.199'/>",
				"</phase>",
				"<phase name='codeinstall' stamp='12.199'>",
				"<dependency type='leaf_type' ctxk='787'/>",
				"<phase_done name='codeinstall' stamp='12.199'/>",
				"</phase>",
				"<code_cache total_blobs='377' nmethods='152' adapters='142' free_code_cache='250142208'/>",
				"<task_done success='1' nmsize='3272' count='1' backedge_count='73158' inlined_bytes='112' stamp='12.199'/>",
				"</task>"
		};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: iload           5    ",
				"7: i2l             ",
				"8: lload_1         ",
				"9: lcmp            ",
				"10: ifge            43   ",
				"13: aload_0         ",
				"14: lload_3         ",
				"15: invokespecial   #70  // Method leaf1:(J)J",
				"18: lstore_3        ",
				"19: aload_0         ",
				"20: lload_3         ",
				"21: invokespecial   #71  // Method leaf2:(J)J",
				"24: lstore_3        ",
				"25: aload_0         ",
				"26: lload_3         ",
				"27: invokespecial   #72  // Method leaf3:(J)J",
				"30: lstore_3        ",
				"31: aload_0         ",
				"32: lload_3         ",
				"33: invokespecial   #73  // Method leaf4:(J)J",
				"36: lstore_3        ",
				"37: iinc            5, 1 ",
				"40: goto            5    ",
				"43: getstatic       #13  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"46: new             #14  // class java/lang/StringBuilder",
				"49: dup             ",
				"50: invokespecial   #15  // Method java/lang/StringBuilder.\"<init>\":()V",
				"53: ldc             #74  // String testLeaf:",
				"55: invokevirtual   #17  // Method java/lang/StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;",
				"58: lload_3         ",
				"59: invokevirtual   #18  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"62: invokevirtual   #19  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"65: invokevirtual   #20  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"68: return          "
					};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testLeaf", new Class[]{long.class});


		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C1, logLines, bytecodeLines);

		assertEquals(9, result.size());

		checkLine(result, 15, "Inlined: Yes", Color.GREEN);
		checkLine(result, 21, "Inlined: Yes", Color.GREEN);
		checkLine(result, 27, "Inlined: Yes", Color.GREEN);
		checkLine(result, 33, "Inlined: Yes", Color.GREEN);
		checkLine(result, 50, "Inlined: Yes", Color.GREEN);
		checkLine(result, 55, "Inlined: Yes", Color.GREEN);
		checkLine(result, 59, "Inlined: Yes", Color.GREEN);
		checkLine(result, 62, "Inlined: Yes", Color.GREEN);
		checkLine(result, 65, "Inlined: Yes", Color.GREEN);
	}

	@Test
	public void testJava8TieredChain()
	{
		String[] logLines = new String[]{
				"<task compile_id='133' compile_kind='osr' method='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog testCallChain (J)V' bytes='57' count='1' backedge_count='60651' iicount='1' osr_bci='5' level='3' stamp='12.043'>",
				"<phase name='buildIR' stamp='12.043'>",
				"<type id='680' name='void'/>",
				"<type id='679' name='long'/>",
				"<klass id='776' name='org/adoptopenjdk/jitwatch/demo/MakeHotSpotLog' flags='1'/>",
				"<method id='777' holder='776' name='testCallChain' return='680' arguments='679' flags='2' bytes='57' iicount='1'/>",
				"<parse method='777'  stamp='12.043'>",
				"<bc code='183' bci='15'/>",
				"<method id='779' holder='776' name='chainA1' return='679' arguments='679' flags='2' bytes='8' compile_id='131' compiler='C2' level='4' iicount='12111'/>",
				"<call method='779' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='3'/>",
				"<method id='781' holder='776' name='chainA2' return='679' arguments='679' flags='2' bytes='10' iicount='12111'/>",
				"<call method='781' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='5'/>",
				"<method id='783' holder='776' name='chainA3' return='679' arguments='679' flags='2' bytes='10' iicount='12111'/>",
				"<call method='783' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='5'/>",
				"<method id='785' holder='776' name='chainA4' return='679' arguments='679' flags='2' bytes='7' iicount='12111'/>",
				"<call method='785' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='3'/>",
				"<type id='678' name='int'/>",
				"<method id='787' holder='776' name='bigMethod' return='679' arguments='679 678' flags='2' bytes='350' compile_id='43' compiler='C2' level='4' iicount='6047'/>",
				"<call method='787' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='21'/>",
				"<method id='789' holder='776' name='chainB1' return='679' arguments='679' flags='2' bytes='8' compile_id='132' compiler='C2' level='4' iicount='16858'/>",
				"<call method='789' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='791' holder='776' name='chainB2' return='679' arguments='679' flags='2' bytes='10' compile_id='130' compiler='C1' level='3' iicount='16858'/>",
				"<call method='791' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='793' holder='776' name='chainB3' return='679' arguments='679' flags='2' bytes='6' iicount='16858'/>",
				"<call method='793' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='38'/>",
				"<klass id='749' name='java/lang/StringBuilder' flags='17'/>",
				"<method id='797' holder='749' name='&lt;init&gt;' return='680' flags='1' bytes='7' iicount='112'/>",
				"<call method='797' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='3'/>",
				"<klass id='747' name='java/lang/AbstractStringBuilder' flags='1024'/>",
				"<method id='799' holder='747' name='&lt;init&gt;' return='680' arguments='678' flags='0' bytes='12' iicount='125'/>",
				"<call method='799' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='1'/>",
				"<klass id='685' name='java/lang/Object' flags='1'/>",
				"<method id='801' holder='685' name='&lt;init&gt;' return='680' flags='1' bytes='1' compile_id='10' compiler='C1' level='1' iicount='447535'/>",
				"<call method='801' instr='invokespecial'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='43'/>",
				"<klass id='686' name='java/lang/String' flags='17'/>",
				"<method id='804' holder='749' name='append' return='749' arguments='686' flags='1' bytes='8' iicount='207'/>",
				"<call method='804' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='806' holder='747' name='append' return='747' arguments='686' flags='1' bytes='50' iicount='240'/>",
				"<call method='806' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='47'/>",
				"<method id='808' holder='749' name='append' return='749' arguments='679' flags='1' bytes='8' iicount='7'/>",
				"<call method='808' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='2'/>",
				"<method id='810' holder='747' name='append' return='747' arguments='679' flags='1' bytes='70' iicount='7'/>",
				"<call method='810' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='50'/>",
				"<method id='812' holder='749' name='toString' return='686' flags='1' bytes='17' iicount='111'/>",
				"<call method='812' instr='invokevirtual'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='13'/>",
				"<klass id='765' name='[C' flags='1041'/>",
				"<method id='814' holder='686' name='&lt;init&gt;' return='680' arguments='765 678 678' flags='1' bytes='62' iicount='260'/>",
				"<call method='814' instr='invokespecial'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='182' bci='53'/>",
				"<klass id='795' name='java/io/PrintStream' flags='1'/>",
				"<method id='816' holder='795' name='println' return='680' arguments='686' flags='1' bytes='24' iicount='7'/>",
				"<call method='816' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='795'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='182' bci='6'/>",
				"<method id='818' holder='795' name='print' return='680' arguments='686' flags='1' bytes='13' iicount='7'/>",
				"<call method='818' instr='invokevirtual'/>",
				"<dependency type='leaf_type' ctxk='795'/>",
				"<inline_success reason='receiver is statically known'/>",
				"<bc code='183' bci='9'/>",
				"<method id='820' holder='795' name='write' return='680' arguments='686' flags='2' bytes='83' iicount='7'/>",
				"<call method='820' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='795'/>",
				"<inline_fail reason='callee is too large'/>",
				"<bc code='183' bci='10'/>",
				"<method id='824' holder='795' name='newLine' return='680' flags='2' bytes='73' iicount='7'/>",
				"<call method='824' instr='invokespecial'/>",
				"<dependency type='leaf_type' ctxk='795'/>",
				"<inline_fail reason='callee is too large'/>",
				"<parse_done stamp='12.046'/>",
				"</parse>",
				"<phase name='optimize_blocks' stamp='12.046'>",
				"<phase_done name='optimize_blocks' stamp='12.046'/>",
				"</phase>",
				"<phase name='optimize_null_checks' stamp='12.046'>",
				"<phase_done name='optimize_null_checks' stamp='12.046'/>",
				"</phase>",
				"<phase_done name='buildIR' stamp='12.046'/>",
				"</phase>",
				"<phase name='emit_lir' stamp='12.047'>",
				"<phase name='lirGeneration' stamp='12.047'>",
				"<phase_done name='lirGeneration' stamp='12.047'/>",
				"</phase>",
				"<phase name='linearScan' stamp='12.047'>",
				"<phase_done name='linearScan' stamp='12.048'/>",
				"</phase>",
				"<phase_done name='emit_lir' stamp='12.048'/>",
				"</phase>",
				"<phase name='codeemit' stamp='12.048'>",
				"<phase_done name='codeemit' stamp='12.049'/>",
				"</phase>",
				"<phase name='codeinstall' stamp='12.049'>",
				"<dependency type='leaf_type' ctxk='795'/>",
				"<phase_done name='codeinstall' stamp='12.049'/>",
				"</phase>",
				"<code_cache total_blobs='357' nmethods='132' adapters='142' free_code_cache='250181248'/>",
				"<task_done success='1' nmsize='3704' count='1' backedge_count='80786' inlined_bytes='149' stamp='12.049'/>",
				"</task>"
			};

		String[] bytecodeLines = new String[]{
				"0: lconst_0        ",
				"1: lstore_3        ",
				"2: iconst_0        ",
				"3: istore          5    ",
				"5: iload           5    ",
				"7: i2l             ",
				"8: lload_1         ",
				"9: lcmp            ",
				"10: ifge            31   ",
				"13: aload_0         ",
				"14: lload_3         ",
				"15: invokespecial   #58  // Method chainA1:(J)J",
				"18: lstore_3        ",
				"19: aload_0         ",
				"20: lload_3         ",
				"21: invokespecial   #59  // Method chainB1:(J)J",
				"24: lstore_3        ",
				"25: iinc            5, 1 ",
				"28: goto            5    ",
				"31: getstatic       #13  // Field java/lang/System.out:Ljava/io/PrintStream;",
				"34: new             #14  // class java/lang/StringBuilder",
				"37: dup             ",
				"38: invokespecial   #15  // Method java/lang/StringBuilder.\"<init>\":()V",
				"41: ldc             #60  // String testCallChain:",
				"43: invokevirtual   #17  // Method java/lang/StringBuilder.append:(Ljava/lang/String;)Ljava/lang/StringBuilder;",
				"46: lload_3         ",
				"47: invokevirtual   #18  // Method java/lang/StringBuilder.append:(J)Ljava/lang/StringBuilder;",
				"50: invokevirtual   #19  // Method java/lang/StringBuilder.toString:()Ljava/lang/String;",
				"53: invokevirtual   #20  // Method java/io/PrintStream.println:(Ljava/lang/String;)V",
				"56: return          "
		};

		IMetaMember member = UnitTestUtil.createTestMetaMember("org.adoptopenjdk.jitwatch.demo.MakeHotSpotLog", "testCallChain", new Class[]{long.class});

		Map<Integer, LineAnnotation> result = buildAnnotations(member, CompilerName.C1, logLines, bytecodeLines);

		assertEquals(7, result.size());

		checkLine(result, 15, "Inlined: Yes", Color.GREEN);
		checkLine(result, 21, "Inlined: Yes", Color.GREEN);
		checkLine(result, 38, "Inlined: Yes", Color.GREEN);
		checkLine(result, 43, "Inlined: Yes", Color.GREEN);
		checkLine(result, 47, "Inlined: Yes", Color.GREEN);
		checkLine(result, 50, "Inlined: Yes", Color.GREEN);
		checkLine(result, 53, "Inlined: Yes", Color.GREEN);
	}

	private Map<Integer, LineAnnotation> buildAnnotations(IMetaMember member, CompilerName compiler, String[] logLines, String[] bytecodeLines)
	{
		TagProcessor tp = new TagProcessor();

		tp.setCompiler(compiler);

		int count = 0;

		Tag tag = null;

		for (String line : logLines)
		{
			line = line.replace("&lt;", S_OPEN_ANGLE);
			line = line.replace("&gt;", S_CLOSE_ANGLE);

			tag = tp.processLine(line);

			if (count++ < logLines.length - 1)
			{
				assertNull(tag);
			}
		}

		assertNotNull(tag);

		member.addJournalEntry(tag);

		// marks member as compiled
		member.setCompiledAttributes(new HashMap<String, String>());

		StringBuilder bytecodeBuilder = new StringBuilder();

		for (String bcLine : bytecodeLines)
		{
			bytecodeBuilder.append(bcLine.trim()).append(S_NEWLINE);
		}

		List<BytecodeInstruction> instructions = BytecodeLoader.parseInstructions(bytecodeBuilder.toString());

		Map<Integer, LineAnnotation> result = new HashMap<>();

		try
		{
			result = new BytecodeAnnotationBuilder().buildBytecodeAnnotations(member, instructions);
		}
		catch (AnnotationException annoEx)
		{
			annoEx.printStackTrace();

			fail();
		}

		return result;
	}

	@Test
	public void testMemberMatchesParseTag()
	{
		String methodName = "length";
		String klassName = "java.lang.String";

		Map<String, String> attrsMethod = new HashMap<>();
		Map<String, String> attrsKlass = new HashMap<>();
		Map<String, String> attrsParse = new HashMap<>();
		Map<String, String> attrsTypeInt = new HashMap<>();

		String idInt = "1";
		String nameInt = "int";

		attrsTypeInt.put(ATTR_ID, idInt);
		attrsTypeInt.put(ATTR_NAME, nameInt);

		Tag tagTypeInt = new Tag(TAG_TYPE, attrsTypeInt, true);

		String methodID = "123";
		String klassID = "456";

		attrsMethod.put(ATTR_NAME, methodName);
		attrsMethod.put(ATTR_ID, methodID);
		attrsMethod.put(ATTR_HOLDER, klassID);
		attrsMethod.put(ATTR_RETURN, idInt);

		Tag tagMethod = new Tag(TAG_METHOD, attrsMethod, true);

		attrsKlass.put(ATTR_NAME, klassName.replace(C_DOT, C_SLASH));
		attrsKlass.put(ATTR_ID, klassID);
		Tag tagKlass = new Tag(TAG_KLASS, attrsKlass, true);

		attrsParse.put(ATTR_METHOD, methodID);
		Tag tagParse = new Tag(TAG_PARSE, attrsParse, false);

		IParseDictionary parseDictionary = new ParseDictionary();
		parseDictionary.setKlass(klassID, tagKlass);
		parseDictionary.setMethod(methodID, tagMethod);
		parseDictionary.setType(idInt, tagTypeInt);

		IMetaMember member = UnitTestUtil.createTestMetaMember(klassName, methodName, new Class[0]);

		assertTrue(JournalUtil.memberMatchesParseTag(member, tagParse, parseDictionary));
	}

	@Test
	public void testIsJournalForCompile2NativeMember()
	{
		String tagText = "<nmethod address='0x00007fb0ef001550' method='sun/misc/Unsafe compareAndSwapLong (Ljava/lang/Object;JJJ)Z' consts_offset='872' count='5000' backedge_count='1' stamp='2.453' iicount='10000' entry='0x00007fb0ef0016c0' size='872' compile_kind='c2n' insts_offset='368' bytes='0' relocation_offset='296' compile_id='28'/>";

		IMetaMember member = UnitTestUtil.createTestMetaMember();

		TagProcessor tp = new TagProcessor();
		Tag tag = tp.processLine(tagText);

		member.getJournal().addEntry(tag);

		assertTrue(JournalUtil.isJournalForCompile2NativeMember(member.getJournal()));
	}

	@Test
	public void testIsNotJournalForCompile2NativeMember()
	{
		String tagText = "<task_done success='1' nmsize='120' count='5000' backedge_count='5100' stamp='14.723'/>";

		IMetaMember member = UnitTestUtil.createTestMetaMember();

		TagProcessor tp = new TagProcessor();
		Tag tag = tp.processLine(tagText);

		member.getJournal().addEntry(tag);

		assertFalse(JournalUtil.isJournalForCompile2NativeMember(member.getJournal()));
	}

	private void checkLine(Map<Integer, LineAnnotation> result, int index, String annotation, Color colour)
	{
		LineAnnotation line = result.get(index);

		assertNotNull(line);

		assertTrue(line.getAnnotation().contains(annotation));
		assertEquals(colour, line.getColour());
	}
	
	@Test
	public void testMemberMatchesParseTagWithExactParams()
	{
		String methodName = "print";
		String klassName = "java.io.PrintStream";
		Class<?>[] params = new Class[]{java.lang.String.class};

		Map<String, String> attrsMethod = new HashMap<>();
		Map<String, String> attrsKlass = new HashMap<>();
		Map<String, String> attrsParse = new HashMap<>();
		
		Map<String, String> attrsTypeVoid = new HashMap<>();
		Map<String, String> attrsTypeString = new HashMap<>();

		String idString = "1";
		String nameString = "java.lang.String";
		
		String idVoid = "2";
		String nameVoid = S_TYPE_NAME_VOID;

		attrsTypeString.put(ATTR_ID, idString);
		attrsTypeString.put(ATTR_NAME, nameString);
		
		attrsTypeVoid.put(ATTR_ID, idVoid);
		attrsTypeVoid.put(ATTR_NAME, nameVoid);

		Tag tagTypeString = new Tag(TAG_TYPE, attrsTypeString, true);
		Tag tagTypeVoid = new Tag(TAG_TYPE, attrsTypeVoid, true);

		String methodID = "123";
		String klassID = "456";

		attrsMethod.put(ATTR_NAME, methodName);
		attrsMethod.put(ATTR_ID, methodID);
		attrsMethod.put(ATTR_HOLDER, klassID);
		attrsMethod.put(ATTR_ARGUMENTS, idString);
		attrsMethod.put(ATTR_RETURN, idVoid);

		Tag tagMethod = new Tag(TAG_METHOD, attrsMethod, true);

		attrsKlass.put(ATTR_NAME, klassName.replace(C_DOT, C_SLASH));
		attrsKlass.put(ATTR_ID, klassID);
		Tag tagKlass = new Tag(TAG_KLASS, attrsKlass, true);

		attrsParse.put(ATTR_METHOD, methodID);
		Tag tagParse = new Tag(TAG_PARSE, attrsParse, false);

		IParseDictionary parseDictionary = new ParseDictionary();
		parseDictionary.setKlass(klassID, tagKlass);
		parseDictionary.setMethod(methodID, tagMethod);
		parseDictionary.setType(idString, tagTypeString);
		parseDictionary.setType(idVoid, tagTypeVoid);

		IMetaMember member = UnitTestUtil.createTestMetaMember(klassName, methodName, params);

		assertTrue(JournalUtil.memberMatchesParseTag(member, tagParse, parseDictionary));
	}
	
	@Test
	public void testMemberDoesNotMatchParseTagWithInexactParams()
	{
		String methodName = "print";
		String klassName = "java.io.PrintStream";
		Class<?>[] params = new Class[]{java.lang.Object.class};

		Map<String, String> attrsMethod = new HashMap<>();
		Map<String, String> attrsKlass = new HashMap<>();
		Map<String, String> attrsParse = new HashMap<>();
		
		Map<String, String> attrsTypeVoid = new HashMap<>();
		Map<String, String> attrsTypeString = new HashMap<>();

		String idString = "1";
		String nameString = "java.lang.String";
		
		String idVoid = "2";
		String nameVoid = S_TYPE_NAME_VOID;

		attrsTypeString.put(ATTR_ID, idString);
		attrsTypeString.put(ATTR_NAME, nameString);
		
		attrsTypeVoid.put(ATTR_ID, idVoid);
		attrsTypeVoid.put(ATTR_NAME, nameVoid);

		Tag tagTypeString = new Tag(TAG_TYPE, attrsTypeString, true);
		Tag tagTypeVoid = new Tag(TAG_TYPE, attrsTypeVoid, true);

		String methodID = "123";
		String klassID = "456";

		attrsMethod.put(ATTR_NAME, methodName);
		attrsMethod.put(ATTR_ID, methodID);
		attrsMethod.put(ATTR_HOLDER, klassID);
		attrsMethod.put(ATTR_ARGUMENTS, idString);
		attrsMethod.put(ATTR_RETURN, idVoid);

		Tag tagMethod = new Tag(TAG_METHOD, attrsMethod, true);

		attrsKlass.put(ATTR_NAME, klassName.replace(C_DOT, C_SLASH));
		attrsKlass.put(ATTR_ID, klassID);
		Tag tagKlass = new Tag(TAG_KLASS, attrsKlass, true);

		attrsParse.put(ATTR_METHOD, methodID);
		Tag tagParse = new Tag(TAG_PARSE, attrsParse, false);

		IParseDictionary parseDictionary = new ParseDictionary();
		parseDictionary.setKlass(klassID, tagKlass);
		parseDictionary.setMethod(methodID, tagMethod);
		parseDictionary.setType(idString, tagTypeString);
		parseDictionary.setType(idVoid, tagTypeVoid);

		IMetaMember member = UnitTestUtil.createTestMetaMember(klassName, methodName, params);

		assertFalse(JournalUtil.memberMatchesParseTag(member, tagParse, parseDictionary));
	}
}