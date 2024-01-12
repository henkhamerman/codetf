Refactoring Types: ['Move Class']
INF/src/com/liferay/tika/metadata/BaseRawMetadataProcessor.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.portal.metadata;

import com.liferay.portal.kernel.exception.PortalException;
import com.liferay.portal.kernel.exception.SystemException;
import com.liferay.portal.kernel.log.Log;
import com.liferay.portal.kernel.log.LogFactoryUtil;
import com.liferay.portal.kernel.metadata.RawMetadataProcessor;
import com.liferay.portal.kernel.util.StringPool;
import com.liferay.portlet.dynamicdatamapping.storage.Fields;

import java.io.File;
import java.io.InputStream;

import java.lang.reflect.Field;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.apache.tika.metadata.ClimateForcast;
import org.apache.tika.metadata.CreativeCommons;
import org.apache.tika.metadata.DublinCore;
import org.apache.tika.metadata.Geographic;
import org.apache.tika.metadata.HttpHeaders;
import org.apache.tika.metadata.MSOffice;
import org.apache.tika.metadata.Message;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.metadata.Property;
import org.apache.tika.metadata.TIFF;
import org.apache.tika.metadata.TikaMetadataKeys;
import org.apache.tika.metadata.TikaMimeKeys;

/**
 * @author Alexander Chow
 */
public abstract class BaseRawMetadataProcessor implements RawMetadataProcessor {

	@Override
	public Map<String, Field[]> getFields() {
		return _fields;
	}

	@Override
	public Map<String, Fields> getRawMetadataMap(
			String extension, String mimeType, File file)
		throws PortalException, SystemException {

		Metadata metadata = extractMetadata(extension, mimeType, file);

		return createDDMFieldsMap(metadata, getFields());
	}

	@Override
	public Map<String, Fields> getRawMetadataMap(
			String extension, String mimeType, InputStream inputStream)
		throws PortalException, SystemException {

		Metadata metadata = extractMetadata(extension, mimeType, inputStream);

		return createDDMFieldsMap(metadata, getFields());
	}

	protected Fields createDDMFields(Metadata metadata, Field[] fields) {
		Fields ddmFields = new Fields();

		for (Field field : fields) {
			Class<?> fieldClass = field.getDeclaringClass();

			String fieldClassName = fieldClass.getSimpleName();

			String name = fieldClassName.concat(
				StringPool.UNDERLINE).concat(field.getName());

			String value = getMetadataValue(metadata, field);

			if (value == null) {
				continue;
			}

			com.liferay.portlet.dynamicdatamapping.storage.Field ddmField =
				new com.liferay.portlet.dynamicdatamapping.storage.Field(
					name, value);

			ddmFields.put(ddmField);
		}

		return ddmFields;
	}

	protected Map<String, Fields> createDDMFieldsMap(
		Metadata metadata, Map<String, Field[]> fieldsMap) {

		Map<String, Fields> ddmFieldsMap = new HashMap<String, Fields>();

		if (metadata == null) {
			return ddmFieldsMap;
		}

		for (String key : fieldsMap.keySet()) {
			Field[] fields = fieldsMap.get(key);

			Fields ddmFields = createDDMFields(metadata, fields);

			Set<String> names = ddmFields.getNames();

			if (names.isEmpty()) {
				continue;
			}

			ddmFieldsMap.put(key, ddmFields);
		}

		return ddmFieldsMap;
	}

	protected abstract Metadata extractMetadata(
			String extension, String mimeType, File file)
		throws PortalException, SystemException;

	protected abstract Metadata extractMetadata(
			String extension, String mimeType, InputStream inputStream)
		throws PortalException, SystemException;

	protected Object getFieldValue(Metadata metadata, Field field) {
		Object fieldValue = null;

		try {
			fieldValue = field.get(metadata);
		}
		catch (IllegalAccessException iae) {
			if (_log.isWarnEnabled()) {
				_log.warn(
					"The property " + field.getName() +
						" will not be added to the metatada set");
			}
		}

		return fieldValue;
	}

	protected String getMetadataValue(Metadata metadata, Field field) {
		Object fieldValue = getFieldValue(metadata, field);

		if (fieldValue instanceof String) {
			return metadata.get((String)fieldValue);
		}

		Property property = (Property)fieldValue;

		return metadata.get(property.getName());
	}

	private static void _addFields(Class<?> clazz, List<Field> fields) {
		for (Field field : clazz.getFields()) {
			fields.add(field);
		}
	}

	private static Log _log = LogFactoryUtil.getLog(
		BaseRawMetadataProcessor.class);

	private static Map<String, Field[]> _fields =
		new HashMap<String, Field[]>();

	static {
		List<Field> fields = new ArrayList<Field>();

		_addFields(ClimateForcast.class, fields);
		_addFields(CreativeCommons.class, fields);
		_addFields(DublinCore.class, fields);
		_addFields(Geographic.class, fields);
		_addFields(HttpHeaders.class, fields);
		_addFields(Message.class, fields);
		_addFields(MSOffice.class, fields);
		_addFields(TIFF.class, fields);
		_addFields(TikaMetadataKeys.class, fields);
		_addFields(TikaMimeKeys.class, fields);
		_addFields(XMPDM.class, fields);

		_fields.put(
			"TIKARAWMETADATA", fields.toArray(new Field[fields.size()]));
	}

}

File: webs/tika-web/docroot/WEB-INF/src/com/liferay/tika/metadata/TikaRawMetadataProcessor.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.portal.metadata;

import com.liferay.portal.kernel.exception.SystemException;
import com.liferay.portal.kernel.io.DummyWriter;
import com.liferay.portal.kernel.log.Log;
import com.liferay.portal.kernel.log.LogFactoryUtil;
import com.liferay.portal.kernel.process.ClassPathUtil;
import com.liferay.portal.kernel.process.ProcessCallable;
import com.liferay.portal.kernel.process.ProcessException;
import com.liferay.portal.kernel.process.ProcessExecutor;
import com.liferay.portal.kernel.util.ArrayUtil;
import com.liferay.portal.kernel.util.FileUtil;
import com.liferay.portal.kernel.util.StreamUtil;
import com.liferay.portal.util.PropsValues;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;

import java.util.concurrent.Future;

import org.apache.commons.compress.archivers.zip.UnsupportedZipFeatureException;
import org.apache.commons.lang.exception.ExceptionUtils;
import org.apache.pdfbox.exceptions.CryptographyException;
import org.apache.poi.EncryptedDocumentException;
import org.apache.tika.exception.TikaException;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.parser.Parser;
import org.apache.tika.sax.WriteOutContentHandler;

import org.xml.sax.ContentHandler;

/**
 * @author Miguel Pastor
 * @author Alexander Chow
 * @author Shuyang Zhou
 */
public class TikaRawMetadataProcessor extends XugglerRawMetadataProcessor {

	public void setParser(Parser parser) {
		_parser = parser;
	}

	protected static Metadata extractMetadata(
			InputStream inputStream, Metadata metadata, Parser parser)
		throws IOException {

		if (metadata == null) {
			metadata = new Metadata();
		}

		ParseContext parserContext = new ParseContext();

		parserContext.set(Parser.class, parser);

		ContentHandler contentHandler = new WriteOutContentHandler(
			new DummyWriter());

		try {
			parser.parse(inputStream, contentHandler, metadata, parserContext);
		}
		catch (Exception e) {
			Throwable throwable = ExceptionUtils.getRootCause(e);

			if ((throwable instanceof CryptographyException) ||
				(throwable instanceof EncryptedDocumentException) ||
				(throwable instanceof UnsupportedZipFeatureException)) {

				if (_log.isWarnEnabled()) {
					_log.warn(
						"Unable to extract metadata from an encrypted file");
				}
			}
			else if (e instanceof TikaException) {
				if (_log.isWarnEnabled()) {
					_log.warn("Unable to extract metadata");
				}
			}
			else {
				_log.error(e, e);
			}

			throw new IOException(e.getMessage());
		}

		// Remove potential security risks

		metadata.remove(XMPDM.ABS_PEAK_AUDIO_FILE_PATH.getName());
		metadata.remove(XMPDM.RELATIVE_PEAK_AUDIO_FILE_PATH.getName());

		return metadata;
	}

	@Override
	protected Metadata extractMetadata(
			String extension, String mimeType, File file)
		throws SystemException {

		Metadata metadata = super.extractMetadata(extension, mimeType, file);

		boolean forkProcess = false;

		if (PropsValues.TEXT_EXTRACTION_FORK_PROCESS_ENABLED) {
			if (ArrayUtil.contains(
					PropsValues.TEXT_EXTRACTION_FORK_PROCESS_MIME_TYPES,
					mimeType)) {

				forkProcess = true;
			}
		}

		if (forkProcess) {
			ExtractMetadataProcessCallable extractMetadataProcessCallable =
				new ExtractMetadataProcessCallable(file, metadata, _parser);

			try {
				Future<Metadata> future = ProcessExecutor.execute(
					ClassPathUtil.getPortalClassPath(),
					extractMetadataProcessCallable);

				return future.get();
			}
			catch (Exception e) {
				throw new SystemException(e);
			}
		}

		InputStream inputStream = null;

		try {
			inputStream = new FileInputStream(file);

			return extractMetadata(inputStream, metadata, _parser);
		}
		catch (IOException ioe) {
			throw new SystemException(ioe);
		}
		finally {
			StreamUtil.cleanUp(inputStream);
		}
	}

	@Override
	protected Metadata extractMetadata(
			String extension, String mimeType, InputStream inputStream)
		throws SystemException {

		Metadata metadata = super.extractMetadata(
			extension, mimeType, inputStream);

		boolean forkProcess = false;

		if (PropsValues.TEXT_EXTRACTION_FORK_PROCESS_ENABLED) {
			if (ArrayUtil.contains(
					PropsValues.TEXT_EXTRACTION_FORK_PROCESS_MIME_TYPES,
					mimeType)) {

				forkProcess = true;
			}
		}

		if (forkProcess) {
			File file = FileUtil.createTempFile();

			try {
				FileUtil.write(file, inputStream);

				ExtractMetadataProcessCallable extractMetadataProcessCallable =
					new ExtractMetadataProcessCallable(file, metadata, _parser);

				Future<Metadata> future = ProcessExecutor.execute(
					ClassPathUtil.getPortalClassPath(),
					extractMetadataProcessCallable);

				return future.get();
			}
			catch (Exception e) {
				throw new SystemException(e);
			}
			finally {
				file.delete();
			}
		}

		try {
			return extractMetadata(inputStream, metadata, _parser);
		}
		catch (IOException ioe) {
			throw new SystemException(ioe);
		}
	}

	private static Log _log = LogFactoryUtil.getLog(
		TikaRawMetadataProcessor.class);

	private Parser _parser;

	private static class ExtractMetadataProcessCallable
		implements ProcessCallable<Metadata> {

		public ExtractMetadataProcessCallable(
			File file, Metadata metadata, Parser parser) {

			_file = file;
			_metadata = metadata;
			_parser = parser;
		}

		@Override
		public Metadata call() throws ProcessException {
			InputStream inputStream = null;

			try {
				inputStream = new FileInputStream(_file);

				return extractMetadata(inputStream, _metadata, _parser);
			}
			catch (IOException ioe) {
				throw new ProcessException(ioe);
			}
			finally {
				if (inputStream != null) {
					try {
						inputStream.close();
					}
					catch (IOException ioe) {
						throw new ProcessException(ioe);
					}
				}
			}
		}

		private static final long serialVersionUID = 1L;

		private File _file;
		private Metadata _metadata;
		private Parser _parser;

	}

}

File: webs/tika-web/docroot/WEB-INF/src/com/liferay/tika/metadata/XMPDM.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.portal.metadata;

import org.apache.tika.metadata.Property;

/**
 * @author Alexander Chow
 */
public interface XMPDM extends org.apache.tika.metadata.XMPDM {

	public static final Property DURATION = Property.externalText(
		"xmpDM:duration");

}

File: webs/tika-web/docroot/WEB-INF/src/com/liferay/tika/metadata/XugglerRawMetadataProcessor.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.portal.metadata;

import com.liferay.portal.kernel.exception.SystemException;
import com.liferay.portal.kernel.lar.PortletDataContext;
import com.liferay.portal.kernel.log.Log;
import com.liferay.portal.kernel.log.LogFactoryUtil;
import com.liferay.portal.kernel.repository.model.FileEntry;
import com.liferay.portal.kernel.util.FileUtil;
import com.liferay.portal.kernel.util.StringBundler;
import com.liferay.portal.kernel.util.StringPool;
import com.liferay.portal.kernel.util.Time;
import com.liferay.portal.kernel.xml.Element;
import com.liferay.portal.kernel.xuggler.XugglerUtil;
import com.liferay.portlet.documentlibrary.util.AudioProcessorUtil;
import com.liferay.portlet.documentlibrary.util.VideoProcessorUtil;

import com.xuggle.xuggler.IContainer;

import java.io.File;
import java.io.InputStream;

import java.text.DecimalFormat;

import org.apache.tika.metadata.Metadata;

/**
 * @author Juan González
 * @author Alexander Chow
 */
public class XugglerRawMetadataProcessor extends BaseRawMetadataProcessor {

	@Override
	public void exportGeneratedFiles(
			PortletDataContext portletDataContext, FileEntry fileEntry,
			Element fileEntryElement)
		throws Exception {

		return;
	}

	@Override
	public void importGeneratedFiles(
			PortletDataContext portletDataContext, FileEntry fileEntry,
			FileEntry importedFileEntry, Element fileEntryElement)
		throws Exception {

		return;
	}

	protected String convertTime(long microseconds) {
		long milliseconds = microseconds / 1000L;

		StringBundler sb = new StringBundler(7);

		sb.append(_decimalFormatter.format(milliseconds / Time.HOUR));
		sb.append(StringPool.COLON);
		sb.append(
			_decimalFormatter.format(milliseconds % Time.HOUR / Time.MINUTE));
		sb.append(StringPool.COLON);
		sb.append(
			_decimalFormatter.format(milliseconds % Time.MINUTE / Time.SECOND));
		sb.append(StringPool.PERIOD);
		sb.append(_decimalFormatter.format(milliseconds % Time.SECOND / 10));

		return sb.toString();
	}

	protected Metadata extractMetadata(File file) throws Exception {
		IContainer container = IContainer.make();

		try {
			Metadata metadata = new Metadata();

			if (container.open(
					file.getCanonicalPath(), IContainer.Type.READ, null) < 0) {

				throw new IllegalArgumentException("Could not open stream");
			}

			if (container.queryStreamMetaData() < 0) {
				throw new IllegalStateException(
					"Could not query stream metadata");
			}

			long microseconds = container.getDuration();

			metadata.set(XMPDM.DURATION, convertTime(microseconds));

			return metadata;
		}
		finally {
			if (container.isOpened()) {
				container.close();
			}
		}
	}

	@Override
	@SuppressWarnings("unused")
	protected Metadata extractMetadata(
			String extension, String mimeType, File file)
		throws SystemException {

		Metadata metadata = null;

		if (!isSupported(mimeType)) {
			return metadata;
		}

		try {
			metadata = extractMetadata(file);
		}
		catch (Exception e) {
			_log.error(e, e);
		}

		return metadata;
	}

	@Override
	@SuppressWarnings("unused")
	protected Metadata extractMetadata(
			String extension, String mimeType, InputStream inputStream)
		throws SystemException {

		Metadata metadata = null;

		File file = null;

		if (!isSupported(mimeType)) {
			return metadata;
		}

		try {
			file = FileUtil.createTempFile(extension);

			FileUtil.write(file, inputStream);

			metadata = extractMetadata(file);
		}
		catch (Exception e) {
			_log.error(e, e);
		}
		finally {
			FileUtil.delete(file);
		}

		return metadata;
	}

	protected boolean isSupported(String mimeType) {
		if (XugglerUtil.isEnabled()) {
			if (AudioProcessorUtil.isAudioSupported(mimeType)) {
				return true;
			}

			if (VideoProcessorUtil.isVideoSupported(mimeType)) {
				return true;
			}
		}

		return false;
	}

	private static Log _log = LogFactoryUtil.getLog(
		XugglerRawMetadataProcessor.class);

	private static DecimalFormat _decimalFormatter = new DecimalFormat("00");

}

File: webs/tika-web/docroot/WEB-INF/src/com/liferay/tika/util/MimeTypesImpl.java
/**
 * Copyright (c) 2000-present Liferay, Inc. All rights reserved.
 *
 * This library is free software; you can redistribute it and/or modify it under
 * the terms of the GNU Lesser General Public License as published by the Free
 * Software Foundation; either version 2.1 of the License, or (at your option)
 * any later version.
 *
 * This library is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
 * details.
 */

package com.liferay.portal.util;

import com.liferay.portal.kernel.exception.SystemException;
import com.liferay.portal.kernel.log.Log;
import com.liferay.portal.kernel.log.LogFactoryUtil;
import com.liferay.portal.kernel.util.ContentTypes;
import com.liferay.portal.kernel.util.GetterUtil;
import com.liferay.portal.kernel.util.MimeTypes;
import com.liferay.portal.kernel.util.SetUtil;
import com.liferay.portal.kernel.util.StreamUtil;
import com.liferay.portal.kernel.util.Validator;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.InputStream;

import java.net.URL;

import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.apache.tika.detect.DefaultDetector;
import org.apache.tika.detect.Detector;
import org.apache.tika.io.CloseShieldInputStream;
import org.apache.tika.io.TikaInputStream;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.mime.MediaType;
import org.apache.tika.mime.MimeTypesReaderMetKeys;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import org.xml.sax.InputSource;

/**
 * @author Jorge Ferrer
 * @author Brian Wing Shun Chan
 * @author Alexander Chow
 */
public class MimeTypesImpl implements MimeTypes, MimeTypesReaderMetKeys {

	public MimeTypesImpl() {
		_detector = new DefaultDetector(
			org.apache.tika.mime.MimeTypes.getDefaultMimeTypes());

		_webImageMimeTypes = SetUtil.fromArray(
			PropsValues.MIME_TYPES_WEB_IMAGES);
	}

	public void afterPropertiesSet() {
		URL url = org.apache.tika.mime.MimeTypes.class.getResource(
			"tika-mimetypes.xml");

		try {
			read(url.openStream());
		}
		catch (Exception e) {
			_log.error("Unable to populate extensions map", e);
		}
	}

	@Override
	public String getContentType(File file) {
		return getContentType(file, file.getName());
	}

	@Override
	public String getContentType(File file, String fileName) {
		if ((file == null) || !file.exists()) {
			return getContentType(fileName);
		}

		InputStream is = null;

		try {
			is = TikaInputStream.get(file);

			return getContentType(is, fileName);
		}
		catch (FileNotFoundException fnfe) {
			return getContentType(fileName);
		}
		finally {
			StreamUtil.cleanUp(is);
		}
	}

	@Override
	public String getContentType(InputStream inputStream, String fileName) {
		if (inputStream == null) {
			return getContentType(fileName);
		}

		String contentType = null;

		TikaInputStream tikaInputStream = null;

		try {
			tikaInputStream = TikaInputStream.get(
				new CloseShieldInputStream(inputStream));

			Metadata metadata = new Metadata();

			metadata.set(Metadata.RESOURCE_NAME_KEY, fileName);

			MediaType mediaType = _detector.detect(tikaInputStream, metadata);

			contentType = mediaType.toString();

			if (contentType.contains("tika")) {
				if (_log.isDebugEnabled()) {
					_log.debug("Retrieved invalid content type " + contentType);
				}

				contentType = getContentType(fileName);
			}

			if (contentType.contains("tika")) {
				if (_log.isDebugEnabled()) {
					_log.debug("Retrieved invalid content type " + contentType);
				}

				contentType = ContentTypes.APPLICATION_OCTET_STREAM;
			}
		}
		catch (Exception e) {
			_log.error(e, e);

			contentType = ContentTypes.APPLICATION_OCTET_STREAM;
		}
		finally {
			StreamUtil.cleanUp(tikaInputStream);
		}

		return contentType;
	}

	@Override
	public String getContentType(String fileName) {
		if (Validator.isNull(fileName)) {
			return ContentTypes.APPLICATION_OCTET_STREAM;
		}

		try {
			Metadata metadata = new Metadata();

			metadata.set(Metadata.RESOURCE_NAME_KEY, fileName);

			MediaType mediaType = _detector.detect(null, metadata);

			String contentType = mediaType.toString();

			if (!contentType.contains("tika")) {
				return contentType;
			}
			else if (_log.isDebugEnabled()) {
				_log.debug("Retrieved invalid content type " + contentType);
			}
		}
		catch (Exception e) {
			_log.error(e, e);
		}

		return ContentTypes.APPLICATION_OCTET_STREAM;
	}

	@Override
	public String getExtensionContentType(String extension) {
		if (Validator.isNull(extension)) {
			return ContentTypes.APPLICATION_OCTET_STREAM;
		}

		return getContentType("A.".concat(extension));
	}

	@Override
	public Set<String> getExtensions(String contentType) {
		Set<String> extensions = _extensionsMap.get(contentType);

		if (extensions == null) {
			extensions = Collections.emptySet();
		}

		return extensions;
	}

	@Override
	public boolean isWebImage(String mimeType) {
		return _webImageMimeTypes.contains(mimeType);
	}

	protected void read(InputStream stream) throws Exception {
		DocumentBuilderFactory documentBuilderFactory =
			DocumentBuilderFactory.newInstance();

		DocumentBuilder documentBuilder =
			documentBuilderFactory.newDocumentBuilder();

		Document document = documentBuilder.parse(new InputSource(stream));

		Element element = document.getDocumentElement();

		if ((element == null) || !MIME_INFO_TAG.equals(element.getTagName())) {
			throw new SystemException("Invalid configuration file");
		}

		NodeList nodeList = element.getChildNodes();

		for (int i = 0; i < nodeList.getLength(); i++) {
			Node node = nodeList.item(i);

			if (node.getNodeType() != Node.ELEMENT_NODE) {
				continue;
			}

			Element childElement = (Element)node;

			if (MIME_TYPE_TAG.equals(childElement.getTagName())) {
				readMimeType(childElement);
			}
		}
	}

	protected void readMimeType(Element element) {
		Set<String> mimeTypes = new HashSet<String>();

		Set<String> extensions = new HashSet<String>();

		String name = element.getAttribute(MIME_TYPE_TYPE_ATTR);

		mimeTypes.add(name);

		NodeList nodeList = element.getChildNodes();

		for (int i = 0; i < nodeList.getLength(); i++) {
			Node node = nodeList.item(i);

			if (node.getNodeType() != Node.ELEMENT_NODE) {
				continue;
			}

			Element childElement = (Element)node;

			if (ALIAS_TAG.equals(childElement.getTagName())) {
				String alias = childElement.getAttribute(ALIAS_TYPE_ATTR);

				mimeTypes.add(alias);
			}
			else if (GLOB_TAG.equals(childElement.getTagName())) {
				boolean isRegex = GetterUtil.getBoolean(
					childElement.getAttribute(ISREGEX_ATTR));

				if (isRegex) {
					continue;
				}

				String pattern = childElement.getAttribute(PATTERN_ATTR);

				if (!pattern.startsWith("*")) {
					continue;
				}

				String extension = pattern.substring(1);

				if (!extension.contains("*") && !extension.contains("?") &&
					!extension.contains("[")) {

					extensions.add(extension);
				}
			}
		}

		for (String mimeType : mimeTypes) {
			_extensionsMap.put(mimeType, extensions);
		}
	}

	private static Log _log = LogFactoryUtil.getLog(MimeTypesImpl.class);

	private Detector _detector;
	private Map<String, Set<String>> _extensionsMap =
		new HashMap<String, Set<String>>();
	private Set<String> _webImageMimeTypes = new HashSet<String>();

}