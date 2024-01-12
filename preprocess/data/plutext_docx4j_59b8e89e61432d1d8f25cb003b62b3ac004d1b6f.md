Refactoring Types: ['Extract Method']
ackaging/packages/WordprocessingMLPackage.java
/*
 *  Copyright 2007-2008, Plutext Pty Ltd.
 *   
 *  This file is part of docx4j.

    docx4j is licensed under the Apache License, Version 2.0 (the "License"); 
    you may not use this file except in compliance with the License. 

    You may obtain a copy of the License at 

        http://www.apache.org/licenses/LICENSE-2.0 

    Unless required by applicable law or agreed to in writing, software 
    distributed under the License is distributed on an "AS IS" BASIS, 
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
    See the License for the specific language governing permissions and 
    limitations under the License.

 */

package org.docx4j.openpackaging.packages;


import java.io.InputStream;
import java.util.Map;
import java.util.Set;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.Marshaller;
import javax.xml.bind.Unmarshaller;
import javax.xml.transform.Source;
import javax.xml.transform.Templates;
import javax.xml.transform.stream.StreamSource;

import org.docx4j.Docx4jProperties;
import org.docx4j.XmlUtils;
import org.docx4j.convert.out.flatOpcXml.FlatOpcXmlCreator;
import org.docx4j.fonts.IdentityPlusMapper;
import org.docx4j.fonts.Mapper;
import org.docx4j.jaxb.Context;
import org.docx4j.model.structure.DocumentModel;
import org.docx4j.model.structure.HeaderFooterPolicy;
import org.docx4j.model.structure.PageDimensions;
import org.docx4j.model.structure.PageSizePaper;
import org.docx4j.openpackaging.contenttype.ContentType;
import org.docx4j.openpackaging.contenttype.ContentTypeManager;
import org.docx4j.openpackaging.contenttype.ContentTypes;
import org.docx4j.openpackaging.exceptions.Docx4JException;
import org.docx4j.openpackaging.exceptions.InvalidFormatException;
import org.docx4j.openpackaging.parts.DocPropsCorePart;
import org.docx4j.openpackaging.parts.DocPropsCustomPart;
import org.docx4j.openpackaging.parts.DocPropsExtendedPart;
import org.docx4j.openpackaging.parts.JaxbXmlPart;
import org.docx4j.openpackaging.parts.Part;
import org.docx4j.openpackaging.parts.WordprocessingML.FontTablePart;
import org.docx4j.openpackaging.parts.WordprocessingML.GlossaryDocumentPart;
import org.docx4j.openpackaging.parts.WordprocessingML.MainDocumentPart;
import org.docx4j.openpackaging.parts.relationships.Namespaces;
import org.docx4j.wml.Document;
import org.docx4j.wml.SectPr;
import org.docx4j.wml.Styles;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;







/**
 * @author jharrop
 *
 */
public class WordprocessingMLPackage extends OpcPackage {
	
	// What is a Word document these days?
	//
	// Well, a package is a logical entity which holds a collection of parts	
	// And a word document is exactly a WordProcessingML package	
	// Which has a Main Document Part, and optionally, a Glossary Document Part

	/* So its a Word doc if:
	 * 1. _rels/.rels tells you where to find an office document
	 * 2. [Content_Types].xml tells you that office document is   
	 *    of content type application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml
	
	 * A minimal docx has:
	 * 
	 * [Content_Types].xml containing:
	 * 1. <Default Extension="rels" ...
	 * 2. <Override PartName="/word/document.xml"...
	 * 
	 * _rels/.rels with a target for word/document.xml
	 * 
	 * word/document.xml
	 */
	
	protected static Logger log = LoggerFactory.getLogger(WordprocessingMLPackage.class);
		
	
	// Main document
	protected MainDocumentPart mainDoc;
	
	// (optional) Glossary document
	protected GlossaryDocumentPart glossaryDoc;
	
	private DocumentModel documentModel;
	public DocumentModel getDocumentModel() {
		if (documentModel==null) {
			documentModel = new DocumentModel(this);
		}
		return documentModel;
	}
	
	private HeaderFooterPolicy headerFooterPolicy;	
	@Deprecated	
	public HeaderFooterPolicy getHeaderFooterPolicy() {
		int last = getDocumentModel().getSections().size();
		if (last>0) {
			// Should always be the case, since we add one,
			// even if the document contains no sectPr
			return getDocumentModel().getSections().get(last-1).getHeaderFooterPolicy();
		} else {
			log.error("Unexpected - zero sections?!");
			return null;
		}
	}
	
	/**
	 * Constructor.  Also creates a new content type manager
	 * 
	 */	
	public WordprocessingMLPackage() {
		super();
		setContentType(new ContentType(ContentTypes.WORDPROCESSINGML_DOCUMENT));
	}
	/**
	 * Constructor.
	 *  
	 * @param contentTypeManager
	 *            The content type manager to use 
	 */
	public WordprocessingMLPackage(ContentTypeManager contentTypeManager) {
		super(contentTypeManager);
		setContentType(new ContentType(ContentTypes.WORDPROCESSINGML_DOCUMENT));
	}
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * from an existing File (.docx zip or .xml Flat OPC).
     *
	 * @param docxFile
	 *            The docx file 
	 */	
	public static WordprocessingMLPackage load(java.io.File docxFile) throws Docx4JException {
		
		return (WordprocessingMLPackage)OpcPackage.load(docxFile);
	}

	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * from an existing stream(.docx zip or .xml Flat OPC).
     *
	 * @param docxFile
	 *            The docx file 
	 */	
	public static WordprocessingMLPackage load(InputStream is) throws Docx4JException {
		
		return (WordprocessingMLPackage)OpcPackage.load(is);
	}
	
	
	public boolean setPartShortcut(Part part, String relationshipType) {
		
//		log.info("setPartShortcut for part " + part.getClass().getName() );
		
		if (relationshipType.equals(Namespaces.PROPERTIES_CORE)) {
			docPropsCorePart = (DocPropsCorePart)part;
			log.debug("Set shortcut for docPropsCorePart");
			return true;			
		} else if (relationshipType.equals(Namespaces.PROPERTIES_EXTENDED)) {
			docPropsExtendedPart = (DocPropsExtendedPart)part;
			log.debug("Set shortcut for docPropsExtendedPart");
			return true;			
		} else if (relationshipType.equals(Namespaces.PROPERTIES_CUSTOM)) {
			docPropsCustomPart = (DocPropsCustomPart)part;
			log.debug("Set shortcut for docPropsCustomPart");
			return true;			
		} else if (relationshipType.equals(Namespaces.DOCUMENT)) {
			mainDoc = (MainDocumentPart)part;
			log.debug("Set shortcut for mainDoc");
			return true;
		} else {	
			return false;
		}
	}
	
	public MainDocumentPart getMainDocumentPart() {
		return mainDoc;
	}
	
    
    /**
     * Use an XSLT to alter the contents of this package.
     * The output of the transformation must be valid
     * pck:package/pck:part format, as emitted by Word 2007.
     * 
     * @param is
     * @param transformParameters
     * @throws Exception
     */    
    public void transform(Templates xslt,
			  Map<String, Object> transformParameters) throws Exception {

    	// Prepare in the input document
    	
		FlatOpcXmlCreator worker = new FlatOpcXmlCreator(this);
		org.docx4j.xmlPackage.Package pkg = worker.get();
    	
		JAXBContext jc = Context.jcXmlPackage;
		Marshaller marshaller=jc.createMarshaller();
		org.w3c.dom.Document doc = org.docx4j.XmlUtils.neww3cDomDocument();
		marshaller.marshal(pkg, doc);
    			
//		javax.xml.bind.util.JAXBResult result = new javax.xml.bind.util.JAXBResult(jc );
		
		// Use constructor which takes Unmarshaller, rather than JAXBContext,
		// so we can set JaxbValidationEventHandler
		Unmarshaller u = jc.createUnmarshaller();
		u.setEventHandler(new org.docx4j.jaxb.JaxbValidationEventHandler());
		javax.xml.bind.util.JAXBResult result = new javax.xml.bind.util.JAXBResult(u );
		
		// Perform the transformation		
		org.docx4j.XmlUtils.transform(doc, xslt, transformParameters, result);
		

//		javax.xml.bind.JAXBElement je = (javax.xml.bind.JAXBElement)result.getResult();
//		org.docx4j.xmlPackage.Package wmlPackageEl = (org.docx4j.xmlPackage.Package)je.getValue();
		org.docx4j.xmlPackage.Package wmlPackageEl = (org.docx4j.xmlPackage.Package)XmlUtils.unwrap(result.getResult());
		
		org.docx4j.convert.in.FlatOpcXmlImporter xmlPackage = new org.docx4j.convert.in.FlatOpcXmlImporter( wmlPackageEl); 
		
		ContentTypeManager ctm = new ContentTypeManager();
		
		Part tmpDocPart = xmlPackage.getRawPart(ctm,  "/word/document.xml", null);
		Part tmpStylesPart = xmlPackage.getRawPart(ctm,  "/word/styles.xml", null);
		
		// This code assumes all the existing rels etc of 
		// the existing main document part are still relevant.
//		if (wmlDocument==null) {
//			log.warn("Couldn't get main document part from package transform result!");			
//		} else {
//			this.getMainDocumentPart().setJaxbElement(wmlDocument);
//		}	
		this.getMainDocumentPart().setJaxbElement(
				((JaxbXmlPart<Document>) tmpDocPart).getJaxbElement() );
//				
//		if (wmlStyles==null) {
//			log.warn("Couldn't get style definitions part from package transform result!");			
//		} else {
//			this.getMainDocumentPart().getStyleDefinitionsPart().setJaxbElement(wmlStyles);
//		}
		this.getMainDocumentPart().getStyleDefinitionsPart(true).setJaxbElement(
				((JaxbXmlPart<Styles>) tmpStylesPart).getJaxbElement() );
    	
    }
    
    @Deprecated
	// since its questionable whether this
	// is important enough to live in WordprocessingMLPackage,
	// and in any case probably should be replaced with a TraversalUtil
	// approach (which wouldn't involve marshal/unmarshall, and 
	// so should be more efficient).    
    public void filter( FilterSettings filterSettings ) throws Exception {

    	if (filterTemplate==null) { // first use
			Source xsltSource = new StreamSource(
				org.docx4j.utils.ResourceUtils.getResource(
						"org/docx4j/openpackaging/packages/filter.xslt"));
			filterTemplate = XmlUtils.getTransformerTemplate(xsltSource);
    	}
    	transform(filterTemplate, filterSettings.getSettings() );
    	
    }

    static Templates filterTemplate;
    
/* There should be a mapper per document,
 * but PhysicalFonts should be system wide.
 * 
 * The only way PhysicalFonts will change
 * is if fonts are added/removed while
 * docx4j is executing (which can happen eg if an
 * obfuscated font part is read)
 */

    public void setFontMapper(Mapper fm) throws Exception {
    	setFontMapper( fm,  true);
    }
    
    /**
     * @param fm
     * @param populate
     * @throws Exception
     * 
     * @since 3.0.1
     */
    public void setFontMapper(Mapper fm, boolean populate) throws Exception {
    	log.debug("setFontMapper invoked");
    	
    	/* The two font mappers included in docx4j (IdentityPlusMapper
    	 * and BestMatchingMapper), both populate physical fonts statically
    	 * when they are constructed.
    	 * 
    	 * So by now, we know what physical fonts exist on the 
    	 * system.
    	 * 
    	 * A mapper is per document.
    	 * 
    	 * This method:
    	 * - adds fonts embedded in the docx to the mapper
    	 * - optionally, populates the mapper for fonts actually used in the docx,  
    	 * 
    	 * Since an embedded font is document specific, it must NOT be added to
    	 * PhysicalFonts! It is ok to have a PhysicalFont object representing it,
    	 * but that should be stored in the document specific mapper object.   
    	 */
    	
    	if (fm == null) {
    		throw new IllegalArgumentException("Font Substituter cannot be null.");
    	}
		fontMapper = fm;
		org.docx4j.wml.Fonts fonts = null;

		// 1.  Get a list of all the fonts in the document
		Set<String> fontsInUse = this.getMainDocumentPart().fontsInUse();
		
//		if ( fm.getClass().getName().equals("org.docx4j.fonts.BestMatchingMapper") ) {
			
			// 2.  For each font, find the closest match on the system (use OO's VCL.xcu to do this)
			//     - do this in a general way, since docx4all needs this as well to display fonts		
			FontTablePart fontTablePart= this.getMainDocumentPart().getFontTablePart();				
			if (fontTablePart==null) {
				log.warn("FontTable missing; creating default part.");
				fontTablePart= new org.docx4j.openpackaging.parts.WordprocessingML.FontTablePart();
				fontTablePart.unmarshalDefaultFonts();
			}
			
			fontTablePart.processEmbeddings(fontMapper);
			
			fonts = (org.docx4j.wml.Fonts)fontTablePart.getJaxbElement();
//		}
		
		if (populate) {
			fontMapper.populateFontMappings(fontsInUse, fonts);
		}
    	
    }

    public Mapper getFontMapper() {
    	if (fontMapper==null) {
    		fontMapper = new IdentityPlusMapper();
    		// This invokes populateFontMappings
    		try {
				setFontMapper(fontMapper);
			} catch (Exception e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
    	}
		return fontMapper;
	}

	private Mapper fontMapper;
	
	

	/**
	 * Creates a WordprocessingMLPackage, using default page size and orientation.
	 * From 2.7.1, these are read from docx4j.properties, or if not found, default
	 * to A4 portrait.
	 */
	public static WordprocessingMLPackage createPackage() throws InvalidFormatException {
		
		String papersize= Docx4jProperties.getProperties().getProperty("docx4j.PageSize", "A4");
		log.info("Using paper size: " + papersize);
		
		String landscapeString = Docx4jProperties.getProperties().getProperty("docx4j.PageOrientationLandscape", "false");
		boolean landscape= Boolean.parseBoolean(landscapeString);
		log.info("Landscape orientation: " + landscape);
		
		return createPackage(
				PageSizePaper.valueOf(papersize), landscape); 
	}
	
	public static WordprocessingMLPackage createPackage(PageSizePaper sz, boolean landscape ) throws InvalidFormatException {
		
				
		// Create a package
		WordprocessingMLPackage wmlPack = new WordprocessingMLPackage();

		// Create main document part
		MainDocumentPart wordDocumentPart = new MainDocumentPart();		
		
		// Create main document part content
		org.docx4j.wml.ObjectFactory factory = Context.getWmlObjectFactory();
		org.docx4j.wml.Body  body = factory.createBody();		
		org.docx4j.wml.Document wmlDocumentEl = factory.createDocument();
		
		wmlDocumentEl.setBody(body);
		
		// Create a basic sectPr using our Page model
		PageDimensions page = new PageDimensions();
		page.setPgSize(sz, landscape);
		
		SectPr sectPr = factory.createSectPr();
		body.setSectPr(sectPr);
		sectPr.setPgSz(  page.getPgSz() );
		sectPr.setPgMar( page.getPgMar() );
				
		// Put the content in the part
		wordDocumentPart.setJaxbElement(wmlDocumentEl);
						
		// Add the main document part to the package relationships
		// (creating it if necessary)
		wmlPack.addTargetPart(wordDocumentPart);
				
		// Create a styles part
		Part stylesPart = new org.docx4j.openpackaging.parts.WordprocessingML.StyleDefinitionsPart();
		try {
			((org.docx4j.openpackaging.parts.WordprocessingML.StyleDefinitionsPart) stylesPart)
					.unmarshalDefaultStyles();
			
			// Add the styles part to the main document part relationships
			// (creating it if necessary)
			wordDocumentPart.addTargetPart(stylesPart); // NB - add it to main doc part, not package!			
			
		} catch (Exception e) {
			// TODO: handle exception
			//e.printStackTrace();	
			log.error(e.getMessage(), e);
		}
		
		// Metadata: docx4j 2.7.1 can populate some of this from docx4j.properties
		// See SaveToZipFile
		DocPropsCorePart core = new DocPropsCorePart();
		org.docx4j.docProps.core.ObjectFactory coreFactory = new org.docx4j.docProps.core.ObjectFactory();
		core.setJaxbElement(coreFactory.createCoreProperties() );
		wmlPack.addTargetPart(core);
			
		
		DocPropsExtendedPart app = new DocPropsExtendedPart();
		org.docx4j.docProps.extended.ObjectFactory extFactory = new org.docx4j.docProps.extended.ObjectFactory();
		app.setJaxbElement(extFactory.createProperties() );
		wmlPack.addTargetPart(app);	
				
		// Return the new package
		return wmlPack;
		
	}
	
	
	@Override
	protected void finalize() throws Throwable {
		try {
			FontTablePart ftp = this.getMainDocumentPart().getFontTablePart();
			if (ftp != null) {
				ftp.deleteEmbeddedFontTempFiles();
			}
		} finally {
			super.finalize();
		}
		
	}

	public static class FilterSettings {
		
		Boolean removeProofErrors = Boolean.FALSE;		
		public void setRemoveProofErrors(boolean val) {
			removeProofErrors = new Boolean(val);
		}

		Boolean removeContentControls = Boolean.FALSE;		
		public void setRemoveContentControls(boolean val) {
			removeContentControls = new Boolean(val);
		}
		
		Boolean removeRsids = Boolean.FALSE;		
		public void setRemoveRsids(boolean val) {
			removeRsids = new Boolean(val);
		}
		
		Boolean tidyForDocx4all = Boolean.FALSE;		
		public void setTidyForDocx4all(boolean val) {
			tidyForDocx4all = new Boolean(val);
		}
		
		
		public Map<String, Object> getSettings() {
			Map<String, Object> settings = new java.util.HashMap<String, Object>();
			
			settings.put("removeProofErrors", removeProofErrors);
			settings.put("removeContentControls", removeContentControls);
			settings.put("removeRsids", removeRsids);
			settings.put("tidyForDocx4all", tidyForDocx4all);
			
			return settings;
		}
		
		
	}


	
}


File: src/main/java/org/docx4j/openpackaging/parts/WordprocessingML/DocumentPart.java
/*
 *  Copyright 2007-2008, Plutext Pty Ltd.
 *   
 *  This file is part of docx4j.

    docx4j is licensed under the Apache License, Version 2.0 (the "License"); 
    you may not use this file except in compliance with the License. 

    You may obtain a copy of the License at 

        http://www.apache.org/licenses/LICENSE-2.0 

    Unless required by applicable law or agreed to in writing, software 
    distributed under the License is distributed on an "AS IS" BASIS, 
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
    See the License for the specific language governing permissions and 
    limitations under the License.

 */

package org.docx4j.openpackaging.parts.WordprocessingML;


import org.docx4j.XmlUtils;
import org.docx4j.jaxb.Context;
import org.docx4j.openpackaging.exceptions.InvalidFormatException;
import org.docx4j.openpackaging.packages.WordprocessingMLPackage;
import org.docx4j.openpackaging.parts.JaxbXmlPartAltChunkHost;
import org.docx4j.openpackaging.parts.Part;
import org.docx4j.openpackaging.parts.PartName;
import org.docx4j.openpackaging.parts.ThemePart;
import org.docx4j.openpackaging.parts.opendope.ComponentsPart;
import org.docx4j.openpackaging.parts.opendope.ConditionsPart;
import org.docx4j.openpackaging.parts.opendope.QuestionsPart;
import org.docx4j.openpackaging.parts.opendope.XPathsPart;
import org.docx4j.openpackaging.parts.relationships.Namespaces;
import org.docx4j.wml.CTEndnotes;
import org.docx4j.wml.CTFootnotes;
import org.docx4j.wml.CTFtnEdn;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Node;



public abstract class DocumentPart<E> extends JaxbXmlPartAltChunkHost<E> {
	
	protected static Logger log = LoggerFactory.getLogger(DocumentPart.class);
	
	
	/** Parts which can be the target of a relationship from either
	 *  the Main Document or the Glossary Document
	 *  
	 *  Microsoft's Microsoft.Office.DocumentFormat.OpenXML has
	 *  no equivalent of this.  
	 *  
	 */ 
	
	protected CommentsPart commentsPart; 	
	protected DocumentSettingsPart documentSettingsPart;	
	protected EndnotesPart endNotesPart; 	
	protected FontTablePart fontTablePart; 
	protected ThemePart themePart;  
	protected FootnotesPart footnotesPart; 
	protected NumberingDefinitionsPart numberingDefinitionsPart; 	
	protected StyleDefinitionsPart styleDefinitionsPart; 	
	protected WebSettingsPart webSettingsPart;
	
	// To access headerParts and footerParts, instead
	// use the DocumentModel.


	public boolean setPartShortcut(Part part) {
		
		if (part == null ){
			return false;
		} else {
			return setPartShortcut(part, part.getRelationshipType() );
		}
		
	}	
		
	public boolean setPartShortcut(Part part, String relationshipType) {
		
		// Since each part knows its relationshipsType,
		// why is this passed in as an arg?
		// Answer: where the relationshipType is ascertained
		// from the rel itself, it is the most authoritative.
		// Note that we normally use the info in [Content_Types]
		// to create a part of the correct type.  This info
		// will not necessary correspond to the info in the rel!
		
		if (relationshipType==null) {
			log.warn("trying to set part shortcut against a null relationship type.");
			return false;
		}
		
		if (relationshipType.equals(Namespaces.FONT_TABLE)) {
			fontTablePart = (FontTablePart)part;
			return true;			
		} else if (relationshipType.equals(Namespaces.THEME)) {
			themePart = (ThemePart)part;
			return true;	
		} else if (relationshipType.equals(Namespaces.STYLES)) {
			styleDefinitionsPart = (StyleDefinitionsPart)part;
			return true;			
		} else if (relationshipType.equals(Namespaces.WEB_SETTINGS)) {
			webSettingsPart = (WebSettingsPart)part;
			return true;	
		} else if (relationshipType.equals(Namespaces.SETTINGS)) {
			documentSettingsPart = (DocumentSettingsPart)part;
			return true;	
		} else if (relationshipType.equals(Namespaces.COMMENTS)) {
			commentsPart = (CommentsPart)part;
			return true;	
		} else if (relationshipType.equals(Namespaces.ENDNOTES)) {
			endNotesPart = (EndnotesPart)part;
			return true;	
		} else if (relationshipType.equals(Namespaces.FOOTNOTES)) {
			footnotesPart = (FootnotesPart)part;
			return true;	
		} else if (relationshipType.equals(Namespaces.NUMBERING)) {
			numberingDefinitionsPart = (NumberingDefinitionsPart)part;
			return true;	
		} else if (part instanceof ConditionsPart) {
			conditionsPart = ((ConditionsPart)part);
			return true;
		} else if (part instanceof QuestionsPart) {
			questionsPart = ((QuestionsPart)part);
			return true;
		} else if (part instanceof XPathsPart) {
			xPathsPart = ((XPathsPart)part);
			return true;
		} else if (part instanceof ComponentsPart) {
			componentsPart = ((ComponentsPart)part);
			return true;
		} else if (part instanceof BibliographyPart) {
			bibliographyPart = ((BibliographyPart)part);
			return true;
			
			// TODO - to be completed.
		} else {	
			return false;
		}
	}
	
	
	/** Other characteristics which both the Main Document and the
	 *  Glossary Document have.
	 */ 
	//private VML background; // [1.2.1]
	
	
	public DocumentPart(PartName partName) throws InvalidFormatException {
		super(partName);
	}

	

	public CommentsPart getCommentsPart() {
		return commentsPart;
	}


	public DocumentSettingsPart getDocumentSettingsPart() {
		return documentSettingsPart;
	}


	public EndnotesPart getEndNotesPart() {
		return endNotesPart;
	}
	
	/**
	 * Does this package contain an endnotes part, with real endnotes
	 * in it?
	 * @return
	 */
	public boolean hasEndnotesPart() {
		if (getEndNotesPart()==null) {
			return false;
		} else {
			// Word seems to add an endnotes part when it adds a footnotes part,
			// so existence of part is not determinative
			CTEndnotes endnotes = getEndNotesPart().getJaxbElement();
			
			if (endnotes.getEndnote().size()<3) {
				// id's 0 & 1 are:
				// <w:endnote w:type="separator" w:id="0">
				// <w:endnote w:type="continuationSeparator" w:id="1">
				return false;
			}
			return true;
		}
	}

	public FootnotesPart getFootnotesPart() {
		return footnotesPart;
	}
	
	public boolean hasFootnotesPart() {
		if (getFootnotesPart()==null) {
			return false;
		} else {
			return true;
		}
	}

	@Deprecated // see instead org.docx4j.convert.out.Converter
	public static Node getFootnote(WordprocessingMLPackage wmlPackage, String id) {	
		
		CTFootnotes footnotes = wmlPackage.getMainDocumentPart().getFootnotesPart().getJaxbElement();
		int pos = Integer.parseInt(id);
		
		// No @XmlRootElement on CTFtnEdn, so .. 
		CTFtnEdn ftn = (CTFtnEdn)footnotes.getFootnote().get(pos);
		Document d = XmlUtils.marshaltoW3CDomDocument( ftn,
				Context.jc, Namespaces.NS_WORD12, "footnote",  CTFtnEdn.class );
		log.debug("Footnote " + id + ": " + XmlUtils.w3CDomNodeToString(d));
		return d;
	}
	
	public FontTablePart getFontTablePart() {
		return fontTablePart;
	}


//	public List getFooterParts() {
//		return footerPart;
//	}
	
//	public List getHeaderParts() {
//		return headerPart;
//	}


	public NumberingDefinitionsPart getNumberingDefinitionsPart() {
		return numberingDefinitionsPart;
	}


	public StyleDefinitionsPart getStyleDefinitionsPart() {
		return getStyleDefinitionsPart(false);
	}
	
	public StyleDefinitionsPart getStyleDefinitionsPart(boolean create) {
		if (styleDefinitionsPart==null
				&& create) {
			// HTML, PDF output won't work without this
			log.info("No StyleDefinitionsPart detected. Adding default part.");
			try {
				styleDefinitionsPart = new StyleDefinitionsPart();
				styleDefinitionsPart.unmarshalDefaultStyles();
				this.addTargetPart(styleDefinitionsPart); 			
				
			} catch (Exception e) {
				log.error(e.getMessage(), e);
			}
		}
		return styleDefinitionsPart;
	}

	public ThemePart getThemePart() {
		return themePart;
	}
	

	public WebSettingsPart getWebSettingsPart() {
		return webSettingsPart;
	}

	private ConditionsPart conditionsPart;
	public ConditionsPart getConditionsPart() {
		return conditionsPart;
	}
//	public void setConditionsPart(ConditionsPart conditionsPart) {
//		this.conditionsPart = conditionsPart;
//	}

	private XPathsPart xPathsPart;
	public XPathsPart getXPathsPart() {
		return xPathsPart;
	}
//	public void setXPathsPart(XPathsPart xPathsPart) {
//		this.xPathsPart = xPathsPart;
//	}
	
	private QuestionsPart questionsPart;
	public QuestionsPart getQuestionsPart() {
		return questionsPart;
	}
	
	private ComponentsPart componentsPart;
	public ComponentsPart getComponentsPart() {
		return componentsPart;
	}
	
	private BibliographyPart bibliographyPart;
	public BibliographyPart getBibliographyPart() {
		return bibliographyPart;
	}
	
}


File: src/main/java/org/docx4j/openpackaging/parts/WordprocessingML/DocumentSettingsPart.java
/* NOTICE: This file contains code licensed to the Apache Software Foundation (ASF) 
 * under one or more contributor license agreements.
 * 
 * This notice is included to meet the condition in clause 4(b) of the License. 
 */

/*
 *  Copyright 2007-2008, Plutext Pty Ltd.
 *   
 *  This file is part of docx4j.

    docx4j is licensed under the Apache License, Version 2.0 (the "License"); 
    you may not use this file except in compliance with the License. 

    You may obtain a copy of the License at 

        http://www.apache.org/licenses/LICENSE-2.0 

    Unless required by applicable law or agreed to in writing, software 
    distributed under the License is distributed on an "AS IS" BASIS, 
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
    See the License for the specific language governing permissions and 
    limitations under the License.

 */

package org.docx4j.openpackaging.parts.WordprocessingML;

import java.math.BigInteger;
import java.security.SecureRandom;
import java.util.Arrays;

import org.docx4j.jaxb.Context;
import org.docx4j.jaxb.McIgnorableNamespaceDeclarator;
import org.docx4j.openpackaging.exceptions.Docx4JException;
import org.docx4j.openpackaging.exceptions.InvalidFormatException;
import org.docx4j.openpackaging.parts.JaxbXmlPartXPathAware;
import org.docx4j.openpackaging.parts.PartName;
import org.docx4j.openpackaging.parts.relationships.Namespaces;
import org.docx4j.org.apache.poi.EncryptedDocumentException;
import org.docx4j.org.apache.poi.poifs.crypt.CryptoFunctions;
import org.docx4j.org.apache.poi.poifs.crypt.HashAlgorithm;
import org.docx4j.wml.BooleanDefaultTrue;
import org.docx4j.wml.CTCompat;
import org.docx4j.wml.CTCompatSetting;
import org.docx4j.wml.CTDocProtect;
import org.docx4j.wml.CTSettings;
import org.docx4j.wml.STAlgClass;
import org.docx4j.wml.STAlgType;
import org.docx4j.wml.STCryptProv;
import org.docx4j.wml.STDocProtect;
//import org.docx4j.wml.STOnOff;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;



public final class DocumentSettingsPart extends JaxbXmlPartXPathAware<CTSettings> { 
	
	private final static Logger log = LoggerFactory.getLogger(DocumentSettingsPart.class);
	
	// This unmarshalls as a JAXBElement; so we override getJaxbElement()
	
	public DocumentSettingsPart(PartName partName) throws InvalidFormatException {
		super(partName);
		init();
	}

	public DocumentSettingsPart() throws InvalidFormatException {
		super(new PartName("/word/settings.xml"));
		init();
	}
	
	public void init() {		
		
		// Used if this Part is added to [Content_Types].xml 
		setContentType(new  org.docx4j.openpackaging.contenttype.ContentType( 
				org.docx4j.openpackaging.contenttype.ContentTypes.WORDPROCESSINGML_SETTINGS));

		// Used when this Part is added to a rels 
		setRelationshipType(Namespaces.SETTINGS);
				
	}
	
	@Override
    protected void setMceIgnorable(McIgnorableNamespaceDeclarator namespacePrefixMapper) {

		/* 
		 * In DocumentSettingsPart, the namespaces are actually used somewhere in the body,
		 * so JAXB will declare them. 
		 * Our job is simply to set the value of ignorable suitable.
		 */

		boolean needW14 = false;
		if (this.jaxbElement.getDocId14()!=null) {
			needW14 = true;
		} else if (this.jaxbElement.getConflictMode() !=null) {
			needW14 = true;
		} else if (this.jaxbElement.getDiscardImageEditingData() !=null) {
			needW14 = true;
		} else if (this.jaxbElement.getDefaultImageDpi() !=null) {
			needW14 = true;
		}
		
		boolean needW15 = false;		
		if (this.jaxbElement.getChartTrackingRefBased()!=null) {
			needW15 = true;
		} else if (this.jaxbElement.getDocId15() !=null) {
			needW15 = true;
		}
		
		String mceIgnorableVal = "";
		if (needW14) {
			mceIgnorableVal = "w14";
		}
		
		if (needW15) {
			mceIgnorableVal += " w15";
		} 
		log.debug(mceIgnorableVal);
		
		this.jaxbElement.setIgnorable(mceIgnorableVal);
				
    }
	
	/**
	 * Get a compatibility setting in the Word namespace, by name
	 * @param name
	 * @return
	 * @throws Docx4JException
	 */
	public CTCompatSetting getWordCompatSetting(String name) throws Docx4JException {
	
		CTCompat compat = this.getContents().getCompat();
		if (compat==null) {
			log.warn("No w:settings/w:compat element");
			return null;
		}
		/* w:name="overrideTableStyleFontSizeAndJustification" 
		 * w:uri="http://schemas.microsoft.com/office/word" 
		 * w:val="1"
		 */
		CTCompatSetting theSetting = null;
		for (CTCompatSetting setting : compat.getCompatSetting() ) {
			if (setting.getUri().equals("http://schemas.microsoft.com/office/word")
					&& setting.getName().equals(name)) {
				theSetting = setting;
				break;
			}
		}
		
		return theSetting;
	}

	public void setWordCompatSetting(String name, String val) throws Docx4JException {
		
		CTCompat compat = this.getContents().getCompat();
		if (compat==null) {
			log.debug("No w:settings/w:compat element; creating..");
		}
		compat = Context.getWmlObjectFactory().createCTCompat();
		this.getContents().setCompat(compat);
		
		CTCompatSetting theSetting = null;
		for (CTCompatSetting setting : compat.getCompatSetting() ) {
			if (setting.getUri().equals("http://schemas.microsoft.com/office/word")
					&& setting.getName().equals(name)) {
				theSetting = setting;
				break;
			}
		}
		
		if (theSetting==null) {
			theSetting = Context.getWmlObjectFactory().createCTCompatSetting();
			theSetting.setUri("http://schemas.microsoft.com/office/word");
			theSetting.setName(name);
			compat.getCompatSetting().add(theSetting);
		}
		theSetting.setVal(val);
	}
	
	
    /**
     * Verifies the documentProtection tag inside settings.xml file 
     * if the protection is enforced (w:enforcement="1") 
     * and if the kind of protection equals to passed (STDocProtect.Enum editValue) 
     *
     * @return true if documentProtection is enforced with option readOnly
     */
    public boolean isEnforcedWith(STDocProtect editValue) {
        CTDocProtect ctDocProtect = this.jaxbElement.getDocumentProtection();

        if (ctDocProtect == null) {
            return false;
        }

        return ctDocProtect.isEnforcement() && ctDocProtect.getEdit().equals(editValue);
    }
    

    /**
     * Enforces the protection with the option specified by passed editValue.<br/>
     * <br/>
     * In the documentProtection tag inside settings.xml file <br/>
     * it sets the value of enforcement to "1" (w:enforcement="1") <br/>
     * and the value of edit to the passed editValue (w:edit="[passed editValue]")<br/>
     * <br/>
     * sample snippet from settings.xml
     * <pre>
     *     &lt;w:settings  ... &gt;
     *         &lt;w:documentProtection w:edit=&quot;[passed editValue]&quot; w:enforcement=&quot;1&quot;/&gt;
     * </pre>
     */
    public void setEnforcementEditValue(org.docx4j.wml.STDocProtect editValue) {
    	
    	setEnforcementEditValue(editValue, null, null);
    }

    /**
     * Enforces the protection with the option specified by passed editValue and password,
     * using rsaFull (sha1) (like Word 2010).
     * 
     * WARNING: this functionality may give a false sense of security, since it only affects
     * the behaviour of Word's user interface. A mischevious user could still edit the document
     * in some other program, and subsequent users would *not* be warned it has been tampered with. 
     *
     * @param editValue the protection type
     * @param password  the plaintext password, if null no password will be applied
     * @param hashAlgo  the hash algorithm - only md2, m5, sha1, sha256, sha384 and sha512 are supported.
     *                  if null, it will default default to sha1
     */
    public void setEnforcementEditValue(org.docx4j.wml.STDocProtect editValue,
                                        String password) {

    	setEnforcementEditValue(editValue, password, HashAlgorithm.sha1);
    }
    
    /**
     * Enforces the protection with the option specified by passed editValue, password, and 
     * HashAlgorithm for the password.

     *
     * @param editValue the protection type
     * @param password  the plaintext password, if null no password will be applied
     * @param hashAlgo  the hash algorithm - only md2, m5, sha1, sha256, sha384 and sha512 are supported.
     *                  if null, it will default default to sha1
     */
    public void setEnforcementEditValue(org.docx4j.wml.STDocProtect editValue,
                                        String password, HashAlgorithm hashAlgo) {
    	
        safeGetDocumentProtection().setEnforcement(true);    	
        safeGetDocumentProtection().setEdit(editValue);
        
        // Word 2010 doesn't enforce TRACKED_CHANGES,
        // unless <w:trackRevisions/> is also set!
        if (editValue==STDocProtect.TRACKED_CHANGES) {
        	if (this.jaxbElement.getTrackRevisions()==null) {
        		this.jaxbElement.setTrackRevisions(new BooleanDefaultTrue());
        	}
        }

        if (password == null) {
        	// unset
            safeGetDocumentProtection().setCryptProviderType(null);
            safeGetDocumentProtection().setCryptAlgorithmClass(null);
            safeGetDocumentProtection().setCryptAlgorithmType(null);
            safeGetDocumentProtection().setCryptAlgorithmSid(null);
            safeGetDocumentProtection().setSalt(null);
            safeGetDocumentProtection().setCryptSpinCount(null);
            safeGetDocumentProtection().setHash(null);
            
            return;
            
        } else {
            final STCryptProv providerType;
            final int sid;
            switch (hashAlgo) {
                case md2:
                    providerType = STCryptProv.RSA_FULL;
                    sid = 1;
                    break;
                case md4:
                    providerType = STCryptProv.RSA_FULL;
                    sid = 2;
                    break;
                case md5:
                    providerType = STCryptProv.RSA_FULL;
                    sid = 3;
                    break;
                case sha1:
                    providerType = STCryptProv.RSA_FULL;
                    sid = 4;
                    break;
                case sha256:
                    providerType = STCryptProv.RSA_AES;
                    sid = 12;
                    break;
                case sha384:
                    providerType = STCryptProv.RSA_AES;
                    sid = 13;
                    break;
                case sha512:
                    providerType = STCryptProv.RSA_AES;
                    sid = 14;
                    break;
                default:
                    throw new EncryptedDocumentException
                            ("Hash algorithm '" + hashAlgo + "' is not supported for document write protection.");
            }


            SecureRandom random = new SecureRandom();
            byte salt[] = random.generateSeed(16);

            // Iterations specifies the number of times the hashing function shall be iteratively run (using each
            // iteration's result as the input for the next iteration).
            int spinCount = 100000;

            if (hashAlgo == null) hashAlgo = HashAlgorithm.sha1;

            String legacyHash = CryptoFunctions.xorHashPasswordReversed(password);
            // Implementation Notes List:
            // --> In this third stage, the reversed byte order legacy hash from the second stage shall
            //     be converted to Unicode hex string representation
            byte hash[] = CryptoFunctions.hashPassword(legacyHash, hashAlgo, salt, spinCount, false);

            safeGetDocumentProtection().setSalt(salt);
            safeGetDocumentProtection().setHash(hash);
            safeGetDocumentProtection().setCryptSpinCount(BigInteger.valueOf(spinCount));
            safeGetDocumentProtection().setCryptAlgorithmType(STAlgType.TYPE_ANY);
            safeGetDocumentProtection().setCryptAlgorithmClass(STAlgClass.HASH);
            safeGetDocumentProtection().setCryptProviderType(providerType);
            safeGetDocumentProtection().setCryptAlgorithmSid(BigInteger.valueOf(sid));
        }
    }

    /**
     * Validates the existing password
     *
     * @param password
     * @return true, only if password was set and equals, false otherwise
     */
    public boolean validateProtectionPassword(String password) {
        BigInteger sid = safeGetDocumentProtection().getCryptAlgorithmSid();
        byte hash[] = safeGetDocumentProtection().getHash();
        byte salt[] = safeGetDocumentProtection().getSalt();
        BigInteger spinCount = safeGetDocumentProtection().getCryptSpinCount();

        if (sid == null || hash == null || salt == null || spinCount == null) return false;

        HashAlgorithm hashAlgo;
        switch (sid.intValue()) {
            case 1:
                hashAlgo = HashAlgorithm.md2;
                break;
            case 2:
                hashAlgo = HashAlgorithm.md4;
                break;
            case 3:
                hashAlgo = HashAlgorithm.md5;
                break;
            case 4:
                hashAlgo = HashAlgorithm.sha1;
                break;
            case 12:
                hashAlgo = HashAlgorithm.sha256;
                break;
            case 13:
                hashAlgo = HashAlgorithm.sha384;
                break;
            case 14:
                hashAlgo = HashAlgorithm.sha512;
                break;
            default:
                return false;
        }

        String legacyHash = CryptoFunctions.xorHashPasswordReversed(password);
        // Implementation Notes List:
        // --> In this third stage, the reversed byte order legacy hash from the second stage shall
        //     be converted to Unicode hex string representation
        byte hash2[] = CryptoFunctions.hashPassword(legacyHash, hashAlgo, salt, spinCount.intValue(), false);

        return Arrays.equals(hash, hash2);
    }

    /**
     * Removes protection enforcement.<br/>
     * In the documentProtection tag inside settings.xml file <br/>
     * it sets the value of enforcement to "0" (w:enforcement="0") <br/>
     */
    public void removeEnforcement() {
//        safeGetDocumentProtection().setEnforcement(STOnOff.X_0);
        safeGetDocumentProtection().setEnforcement(false);    	
    }	
    
    private CTDocProtect safeGetDocumentProtection() {
    	
    	if (this.getJaxbElement()==null) {
    		this.jaxbElement=new CTSettings();
    	}
    	
        CTDocProtect documentProtection = this.jaxbElement.getDocumentProtection();
        if (documentProtection == null) {
            documentProtection = Context.getWmlObjectFactory().createCTDocProtect();
            this.jaxbElement.setDocumentProtection(documentProtection);
        }
        return this.jaxbElement.getDocumentProtection();
    }    
}


File: src/main/java/org/docx4j/openpackaging/parts/WordprocessingML/StyleDefinitionsPart.java
/*
 *  Copyright 2007-2008, Plutext Pty Ltd.
 *   
 *  This file is part of docx4j.

    docx4j is licensed under the Apache License, Version 2.0 (the "License"); 
    you may not use this file except in compliance with the License. 

    You may obtain a copy of the License at 

        http://www.apache.org/licenses/LICENSE-2.0 

    Unless required by applicable law or agreed to in writing, software 
    distributed under the License is distributed on an "AS IS" BASIS, 
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
    See the License for the specific language governing permissions and 
    limitations under the License.

 */

package org.docx4j.openpackaging.parts.WordprocessingML;

import java.io.IOException;
import java.math.BigInteger;
import java.util.List;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Unmarshaller;

import org.docx4j.XmlUtils;
import org.docx4j.jaxb.Context;
import org.docx4j.model.styles.BrokenStyleRemediator;
import org.docx4j.openpackaging.exceptions.Docx4JException;
import org.docx4j.openpackaging.exceptions.InvalidFormatException;
import org.docx4j.openpackaging.parts.JaxbXmlPartXPathAware;
import org.docx4j.openpackaging.parts.PartName;
import org.docx4j.openpackaging.parts.relationships.Namespaces;
import org.docx4j.utils.ResourceUtils;
import org.docx4j.wml.DocDefaults;
import org.docx4j.wml.HpsMeasure;
import org.docx4j.wml.PPr;
import org.docx4j.wml.PPrBase.Spacing;
import org.docx4j.wml.RPr;
import org.docx4j.wml.Style;
import org.docx4j.wml.Style.BasedOn;
import org.docx4j.wml.Styles;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


public final class StyleDefinitionsPart extends JaxbXmlPartXPathAware<Styles> {
	
	private static Logger log = LoggerFactory.getLogger(StyleDefinitionsPart.class);		
	
	public StyleDefinitionsPart(PartName partName) throws InvalidFormatException {
		super(partName);
		init();
	}

	public StyleDefinitionsPart() throws InvalidFormatException {
		super(new PartName("/word/styles.xml"));
		init();
	}
	
	public void init() {
		// Used if this Part is added to [Content_Types].xml 
		setContentType(new  org.docx4j.openpackaging.contenttype.ContentType( 
				org.docx4j.openpackaging.contenttype.ContentTypes.WORDPROCESSINGML_STYLES));

		// Used when this Part is added to a rels 
		setRelationshipType(Namespaces.STYLES);
	}
	
	// A variety of pre-defined styles, available for use in a StyleDefinitionsPart.
	private static java.util.Map<String, org.docx4j.wml.Style>  knownStyles = null;
	
	// private PropertyResolver propertyResolver;
	
	@Override
	public void setJaxbElement(Styles jaxbElement) {
		super.setJaxbElement(jaxbElement);
		// Null out cached values which now point to unrelated objects
		styleDocDefaults=null;
	    defaultCharacterStyle = null;
	    defaultParagraphStyle = null;
	    defaultTableStyle = null;
	    css=null;
	}
	
    
//	@Override
//    public Styles unmarshal(org.w3c.dom.Element el) throws JAXBException {
//    	
//    	// Note: This is used when we read in a pkg:package 
//
//		try {
//
//			Unmarshaller u = jc.createUnmarshaller();
//						
//			u.setEventHandler(new org.docx4j.jaxb.JaxbValidationEventHandler());
//
//			jaxbElement = (Styles) u.unmarshal( el );
//			
//			return jaxbElement;
//			
//		} catch (JAXBException e) {
//			// TODO Auto-generated catch block
//			e.printStackTrace();
//			return null;
//		}
//	}

    
    /**
     * Unmarshal a default set of styles, useful when creating this
     * part from scratch. 
     *
     * @return the newly created root object of the java content tree 
     *
     * @throws JAXBException 
     *     If any unexpected errors occur while unmarshalling
     */
    public Object unmarshalDefaultStyles() throws JAXBException {
    	
    	
//    	Throwable t = new Throwable();
//    	t.printStackTrace();
    	  
    		java.io.InputStream is = null;
			try {
				//Works in Eclipse if the resource is in source/main/java
				//is = getResource("styles.xml");
				
				// Works in Eclipse - not absence of leading '/'
				is = ResourceUtils.getResourceViaProperty("docx4j.openpackaging.parts.WordprocessingML.StyleDefinitionsPart.DefaultStyles",
						"org/docx4j/openpackaging/parts/WordprocessingML/styles.xml");
				
					// styles.xml defines a small subset of common styles
					// (it is a much smaller set of styles than KnownStyles.xml)
				
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}    		
    	
    	return unmarshal( is );    // side-effect is to set jaxbElement 	
    }
    
    private static void initKnownStyles() {

//    	Throwable t = new Throwable();
//    	t.printStackTrace();
    	
		java.io.InputStream is = null;
		try {
			is = ResourceUtils.getResourceViaProperty("docx4j.openpackaging.parts.WordprocessingML.StyleDefinitionsPart.KnownStyles",
					"org/docx4j/openpackaging/parts/WordprocessingML/KnownStyles.xml");						
			
			JAXBContext jc = Context.jc;
			Unmarshaller u = jc.createUnmarshaller();			
			u.setEventHandler(new org.docx4j.jaxb.JaxbValidationEventHandler());

			org.docx4j.wml.Styles styles = (org.docx4j.wml.Styles)u.unmarshal( is );			
			
			knownStyles = new java.util.HashMap<String, org.docx4j.wml.Style>();
			
			for ( org.docx4j.wml.Style s : styles.getStyle() ) {				
				knownStyles.put(s.getStyleId(), s);				
			}
			
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}    		
    	
		
    }

	/**
	 * Returns a map of styles defined in docx4j's KnownStyles.xml
	 * (not styles defined in your pkg)
	 * @return
	 */
	public static java.util.Map<String, org.docx4j.wml.Style> getKnownStyles() {
		if (knownStyles==null) {
			initKnownStyles();
		}
		return knownStyles;
	}
    
	private Style styleDocDefaults;
	
	/**
	 * Manufacture a paragraph style from the following, so it can be used as the 
	 * root of our paragraph style tree.
	 * 
	 * 	<w:docDefaults>
			<w:rPrDefault>
				<w:rPr>
					<w:rFonts w:asciiTheme="minorHAnsi" w:eastAsiaTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi" w:cstheme="minorBidi" />
					<w:sz w:val="22" />
					<w:szCs w:val="22" />
					<w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA" />
				</w:rPr>
			</w:rPrDefault>
			<w:pPrDefault>
				<w:pPr>
					<w:spacing w:after="200" w:line="276" w:lineRule="auto" />
				</w:pPr>
			</w:pPrDefault>
		</w:docDefaults>
		
		BEWARE: in a table, paragraph style ppr trumps table style ppr.
		The effect of including w:docDefaults in the style hierarchy
		is that they trump table style ppr, but they should not!
		
	 * There is no need for a doc defaults character style.
	 * The reason for this is that Word seems to ignore Default Paragraph Style!
	 * So the run formatting comes from paragraph style + explicit character style (if any),
	 * plus direct formatting.
		

	 */
    public void createVirtualStylesForDocDefaults() throws Docx4JException {
    	
    	if (styleDocDefaults!=null) return; // been done already
    	
    	String ROOT_NAME = "DocDefaults";

    	// could be in docx which we saved and are now re-opening
    	styleDocDefaults = getStyleById(this.getJaxbElement().getStyle(), ROOT_NAME);
    	if (styleDocDefaults==null) {

        	styleDocDefaults = Context.getWmlObjectFactory().createStyle();
        	styleDocDefaults.setStyleId(ROOT_NAME);
        	
    		this.getJaxbElement().getStyle().add(styleDocDefaults);
    		
    	} else {
    		
    		log.debug("Found existing style named " + ROOT_NAME);
    		log.debug(XmlUtils.marshaltoString(styleDocDefaults, true, true));
    		
        	// TODO: could be a name collision; some other app using that name :-(
    		// We could check whether normal is based on it (see towards end of this method)
    		
    		if (styleDocDefaults.getRPr()!=null) {
        		log.debug(".. reusing");
    			return;
    		} else {
        		log.debug(".. but no rPr, so re-creating");    			
    		}
    	}
    	
    	styleDocDefaults.setType("paragraph");
    	
		org.docx4j.wml.Style.Name n = Context.getWmlObjectFactory().createStyleName();
    	n.setVal(ROOT_NAME);
    	styleDocDefaults.setName(n);
    			
		// Initialise docDefaults		
		DocDefaults docDefaults = this.getJaxbElement().getDocDefaults(); 		
		
		if (docDefaults == null) {
			log.info("No DocDefaults present");
			// The only way this can happen is if the
			// styles definition part is missing the docDefaults element
			// (these are present in docs created from Word, and
			// in our default styles, so maybe the user created it using
			// some 3rd party program?)
			try {

				docDefaults = (DocDefaults) XmlUtils
						.unmarshalString(docDefaultsString);
			} catch (JAXBException e) {
				throw new Docx4JException("Problem unmarshalling "
						+ docDefaultsString, e);
			}
		}

		// Setup documentDefaultPPr
		PPr documentDefaultPPr;
		if (docDefaults.getPPrDefault() == null) {
			log.info("No PPrDefault present");
			try {
				documentDefaultPPr = (PPr) XmlUtils
						.unmarshalString(pPrDefaultsString);
			} catch (JAXBException e) {
				throw new Docx4JException("Problem unmarshalling "
						+ pPrDefaultsString, e);
			}

		} else {
			documentDefaultPPr = docDefaults.getPPrDefault().getPPr();
			if (documentDefaultPPr==null) {
				documentDefaultPPr = Context.getWmlObjectFactory().createPPr();
			}
		}
		
		// If the docDefaults have no setting for w:spacing
		// then add it:
		if (documentDefaultPPr.getSpacing()==null) {
			Spacing spacing = Context.getWmlObjectFactory().createPPrBaseSpacing();
			documentDefaultPPr.setSpacing(spacing);
			spacing.setBefore(BigInteger.ZERO);
			spacing.setAfter(BigInteger.ZERO);
			spacing.setLine(BigInteger.valueOf(240));
		}

		// Setup documentDefaultRPr
		RPr documentDefaultRPr;
		if (docDefaults.getRPrDefault() == null) {
			log.info("No RPrDefault present");
			try {
				documentDefaultRPr = (RPr) XmlUtils
						.unmarshalString(rPrDefaultsString);
					// that includes font size 10
			} catch (JAXBException e) {
				throw new Docx4JException("Problem unmarshalling "
						+ rPrDefaultsString, e);
			}
		} else {
			documentDefaultRPr = docDefaults.getRPrDefault().getRPr();
			if (documentDefaultRPr==null) {
				documentDefaultRPr = Context.getWmlObjectFactory().createRPr();
			}
			// If default font size is not specified, set it to match Word default when unspecified (ie 10)
			// It is useful to have this explicitly, especially for XHTML Import
//	        <w:sz w:val="20"/>
//	        <w:szCs w:val="20"/>			
			if (documentDefaultRPr.getSz()==null) {
				HpsMeasure s10pt = Context.getWmlObjectFactory().createHpsMeasure();
				s10pt.setVal(BigInteger.valueOf(20));
				documentDefaultRPr.setSz(s10pt);
			}
			if (documentDefaultRPr.getSzCs()==null) {
				HpsMeasure s10pt = Context.getWmlObjectFactory().createHpsMeasure();
				s10pt.setVal(BigInteger.valueOf(20));
				documentDefaultRPr.setSzCs(s10pt);
			}
		}
    	
		styleDocDefaults.setPPr(documentDefaultPPr);
		styleDocDefaults.setRPr(documentDefaultRPr);
		
		// Now point Normal at this
		Style normal = getDefaultParagraphStyle();
		if (normal==null) {
			log.info("No default paragraph style!!");
			normal = Context.getWmlObjectFactory().createStyle();
			normal.setType("paragraph");
			normal.setStyleId("Normal");
			
			n = Context.getWmlObjectFactory().createStyleName();
			n.setVal("Normal");
			normal.setName(n);
			this.getJaxbElement().getStyle().add(normal);	
			
			normal.setDefault(Boolean.TRUE); // @since 3.2.0
		}
		
		BasedOn based = Context.getWmlObjectFactory().createStyleBasedOn();
		based.setVal(ROOT_NAME);		
		normal.setBasedOn(based);
		
		log.debug("Set virtual style, id '" + styleDocDefaults.getStyleId() + "', name '"+ styleDocDefaults.getName().getVal() + "'");
		
		log.debug(XmlUtils.marshaltoString(styleDocDefaults, true, true));
		
		
    	
    }
    
    /**
     * @param id
     * @return
     * @since 3.0.0
     */
    public Style getStyleById(String id) {
    	
		return getStyleById( this.getJaxbElement().getStyle(), id ); 				

    }

    /**
     * @param id
     * @return
     * @since 3.0.1
     */
    private static Style getStyleById(List<Style> styles, String id) {
    	
		for ( org.docx4j.wml.Style s : styles ) {	
			
			if (s.getStyleId()==null) {
				BrokenStyleRemediator.remediate(s);
			}
			
			if( s.getStyleId()!=null
					&& s.getStyleId().equals(id) ) {
				return s;
			}
		}
    	return null;
    }
    
    private Style defaultCharacterStyle;
    public Style getDefaultCharacterStyle() {
    	
    	if (defaultCharacterStyle==null) {
    		defaultCharacterStyle = getDefaultStyle("character");
    	}
    	// OpenOffice conversion to docx
    	// doesn't necessarily contain a default character style
    	// so manufacture one
    	if (defaultCharacterStyle==null) {
    		try {
				defaultCharacterStyle = (Style)XmlUtils.unmarshalString(DEFAULT_CHARACTER_STYLE_DEFAULT);
				this.getJaxbElement().getStyle().add(defaultCharacterStyle);
			} catch (JAXBException e) {
				e.printStackTrace();
			}
    	}
		return defaultCharacterStyle;
    }
    
    private final static String DEFAULT_CHARACTER_STYLE_DEFAULT = "<w:style w:type=\"character\" w:default=\"1\" w:styleId=\"DefaultParagraphFont\" " + Namespaces.W_NAMESPACE_DECLARATION + "><w:name w:val=\"Default Paragraph Font\" /></w:style>";
    
    
    
    private Style defaultParagraphStyle;
    /**
     * if this returns null; invoke createVirtualStylesForDocDefaults() @since 3.2.0 then try again
     * 
     * @return
     */
    public Style getDefaultParagraphStyle() {
    	
    	if (defaultParagraphStyle==null) {
    		defaultParagraphStyle = getDefaultStyle("paragraph");
    	}
    	// OpenOffice conversion to docx
    	// doesn't set default, so use name
    	// (alternatively, could use id=style0)
    	if (defaultParagraphStyle==null) {
    		for ( org.docx4j.wml.Style s : this.getJaxbElement().getStyle() ) {				
    			if( s.getType().equals("paragraph")
    					&& s.getName()!=null
    					&& s.getName().getVal().equals("Default") ) {
    				log.debug("Style with name " + s.getName().getVal() + ", id '" + s.getStyleId() + "' is default " + s.getType() + " style");
    				defaultParagraphStyle=s;
    				break;
    			}
    		}    		
    	}
    	// try using id=style0
    	if (defaultParagraphStyle==null) {
    		for ( org.docx4j.wml.Style s : this.getJaxbElement().getStyle() ) {				
    			if( s.getType().equals("paragraph")
    					&& s.getStyleId().equals("style0") ) {
    				log.debug("Style with name " + s.getName().getVal() + ", id '" + s.getStyleId() + "' is default " + s.getType() + " style");
    				defaultParagraphStyle=s;
    				break;
    			}
    		}    		
    	}
    
    	
		return defaultParagraphStyle;
    }
    
    private Style defaultTableStyle;
    /**
     * @since 3.0
     */
    public Style getDefaultTableStyle() {
    	
    	if (defaultTableStyle==null) {
    		defaultTableStyle = getDefaultStyle("table");
    	}
		return defaultTableStyle;
    }
    
    private Style getDefaultStyle(String type) {
    	
		for ( org.docx4j.wml.Style s : this.getJaxbElement().getStyle() ) {				
			if( s.isDefault() && s.getType().equals(type)) {
				log.debug("Style with name " + s.getName().getVal() + ", id '" + s.getStyleId() + "' is default " + s.getType() + " style");
				return s;
			}
		}
		return null;
    }
    
    
	final static String wNamespaceDec = " xmlns:w=\"" + Namespaces.NS_WORD12 + "\""; 

	public final static String rPrDefaultsString = "<w:rPr" + wNamespaceDec + ">"
		// Word 2007 still uses Times New Roman if there is no theme part, and we'd like to replicate that 
        // + "<w:rFonts w:asciiTheme=\"minorHAnsi\" w:eastAsiaTheme=\"minorHAnsi\" w:hAnsiTheme=\"minorHAnsi\" w:cstheme=\"minorBidi\" />"
        + "<w:sz w:val=\"20\" />"  // was 11 prior to 3.01, but Word default in absence of this setting is 10.
        + "<w:szCs w:val=\"20\" />"
        + "<w:lang w:val=\"en-US\" w:eastAsia=\"en-US\" w:bidi=\"ar-SA\" />"
      + "</w:rPr>";
	public final static String pPrDefaultsString = "<w:pPr" + wNamespaceDec + ">"
	        + "<w:spacing w:after=\"200\" w:line=\"276\" w:lineRule=\"auto\" />"
	      + "</w:pPr>";
	public final static String docDefaultsString = "<w:docDefaults" + wNamespaceDec + ">"
	    + "<w:rPrDefault>"
	    + 	rPrDefaultsString
	    + "</w:rPrDefault>"
	    + "<w:pPrDefault>"
	    + 	pPrDefaultsString
	    + "</w:pPrDefault>"
	  + "</w:docDefaults>";
	

	/**
	 * It is convenient to have a CSS representation of styles,
	 * and this part is a natural place to store it.
	 * 
	 * HtmlCssHelper contains a method createCssForStyles which
	 * relies on StyleTree to generate CSS.  
	 */
	private String css;
	public String getCss() {
		return css;
	}
	public void setCss(String css) {
		this.css = css;
	}
	
	/**
	 * For a run/character style return its linked paragraph style (if any),
	 * or vice versa.
	 * 
	 * @param rStyleVal
	 * @return
	 */
	public Style getLinkedStyle(String rStyleVal) {
		
		Style rStyle = getStyleById(rStyleVal);
		if (rStyle==null) {
			log.info("Couldn't find rStyle " + rStyleVal);
			return null;
		} else {
			// We have a run level style.  Is there a linked pStyle?
			Style.Link linkedStyle = rStyle.getLink();
			if (linkedStyle==null) {
				log.info("No linked style for rStyle " + rStyleVal);							
				return null;
			} else {
				String pStyleVal = linkedStyle.getVal();
				log.debug(rStyleVal + " is linked to style " + pStyleVal );
				Style pStyle = getStyleById(pStyleVal);
				
				if (pStyle==null) {
					log.info("Couldn't find linked pStyle " + pStyleVal 
							+ " for rStyle " + rStyleVal);		
				}
				return pStyle;
			}
		}
	}

	
    
//	public static void main(String[] args) throws Exception {
//		
//		StyleDefinitionsPart sdp = new StyleDefinitionsPart ();		
//		sdp.initKnownStyles();
//    
//	}    
}
