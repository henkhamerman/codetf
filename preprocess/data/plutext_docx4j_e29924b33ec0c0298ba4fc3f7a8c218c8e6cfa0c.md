Refactoring Types: ['Extract Method', 'Move Class']
le/EncryptionDocument.java
package org.apache.poi.poifs.crypt.agile;

import com.microsoft.schemas.office.x2006.encryption.CTEncryption;

// Reverse engineered; specific to docx4j

public class EncryptionDocument 
{
	CTEncryption  encryption = null;
	
    /**
     * Gets the "encryption" element
     */
    public com.microsoft.schemas.office.x2006.encryption.CTEncryption getEncryption()
    {
    	return encryption;
    }
    
    /**
     * Sets the "encryption" element
     */
    public void setEncryption(com.microsoft.schemas.office.x2006.encryption.CTEncryption encryption)
    {
        this.encryption = encryption;
    }
    
    /**
     * Appends and returns a new empty "encryption" element
     */
    public com.microsoft.schemas.office.x2006.encryption.CTEncryption addNewEncryption()
    {
    	encryption = new CTEncryption();
    	return encryption;
    }
}


File: src/main/java/org/apache/poi/poifs/dev/POIFSDump.java
/* ====================================================================
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
==================================================================== */
package org.apache.poi.poifs.dev;

import org.apache.poi.poifs.filesystem.*;

import java.io.FileInputStream;
import java.io.File;
import java.io.IOException;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.util.Iterator;

/**
 * Dump internal structure of a OLE2 file into file system
 */
public class POIFSDump {

    public static void main(String[] args) throws Exception {
        for (int i = 0; i < args.length; i++) {
            System.out.println("Dumping " + args[i]);
            FileInputStream is = new FileInputStream(args[i]);
            NPOIFSFileSystem fs = new NPOIFSFileSystem(is);
            is.close();

            DirectoryEntry root = fs.getRoot();
            File file = new File(root.getName());
            file.mkdir();

            dump(root, file);
        }
   }


    public static void dump(DirectoryEntry root, File parent) throws IOException {
        for(Iterator<Entry> it = root.getEntries(); it.hasNext();){
            Entry entry = it.next();
            if(entry instanceof DocumentNode){
                DocumentNode node = (DocumentNode)entry;
                DocumentInputStream is = new DocumentInputStream(node);
                byte[] bytes = new byte[node.getSize()];
                is.read(bytes);
                is.close();

                OutputStream out = new FileOutputStream(new File(parent, node.getName().trim()));
                try {
                	out.write(bytes);
                } finally {
                	out.close();
                }
            } else if (entry instanceof DirectoryEntry){
                DirectoryEntry dir = (DirectoryEntry)entry;
                File file = new File(parent, entry.getName());
                file.mkdir();
                dump(dir, file);
            } else {
                System.err.println("Skipping unsupported POIFS entry: " + entry);
            }
        }
    }
}


File: src/main/java/org/apache/poi/poifs/dev/POIFSHeaderDumper.java
/* ====================================================================
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
==================================================================== */

package org.apache.poi.poifs.dev;

import java.io.FileInputStream;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

import org.apache.poi.poifs.common.POIFSBigBlockSize;
import org.apache.poi.poifs.common.POIFSConstants;
import org.apache.poi.poifs.property.PropertyTable;
import org.apache.poi.poifs.storage.BlockAllocationTableReader;
import org.apache.poi.poifs.storage.BlockList;
import org.apache.poi.poifs.storage.HeaderBlock;
import org.apache.poi.poifs.storage.ListManagedBlock;
import org.apache.poi.poifs.storage.RawDataBlockList;
import org.apache.poi.poifs.storage.SmallBlockTableReader;
import org.apache.poi.util.HexDump;
import org.apache.poi.util.IntList;

/**
 * A very low level debugging tool, for printing out core 
 *  information on the headers and FAT blocks.
 * You probably only want to use this if you're trying
 *  to understand POIFS, or if you're trying to track
 *  down the source of corruption in a file.
 */
public class POIFSHeaderDumper {
	/**
	 * Display the entries of multiple POIFS files
	 *
	 * @param args the names of the files to be displayed
	 */
	public static void main(final String args[]) throws Exception {
		if (args.length == 0) {
			System.err.println("Must specify at least one file to view");
			System.exit(1);
		}

		for (int j = 0; j < args.length; j++) {
		   viewFile(args[j]);
		}
	}

	public static void viewFile(final String filename) throws Exception {
		InputStream inp = new FileInputStream(filename);
		
		// Header
		HeaderBlock header_block = new HeaderBlock(inp);
		displayHeader(header_block);
		
		// Raw blocks
      POIFSBigBlockSize bigBlockSize = header_block.getBigBlockSize();
      RawDataBlockList data_blocks = new RawDataBlockList(inp, bigBlockSize);
      displayRawBlocksSummary(data_blocks);
      
      // Main FAT Table
      BlockAllocationTableReader batReader =
         new BlockAllocationTableReader(
            header_block.getBigBlockSize(),
            header_block.getBATCount(),
            header_block.getBATArray(),
            header_block.getXBATCount(),
            header_block.getXBATIndex(),
            data_blocks);
      displayBATReader(batReader);

      // Properties Table
      PropertyTable properties =
         new PropertyTable(header_block, data_blocks);
      
      // Mini Fat
      BlockList sbat = 
         SmallBlockTableReader.getSmallDocumentBlocks(
               bigBlockSize, data_blocks, properties.getRoot(),
               header_block.getSBATStart()
         );
   }

	public static void displayHeader(HeaderBlock header_block) throws Exception {
	   System.out.println("Header Details:");
	   System.out.println(" Block size: " + header_block.getBigBlockSize().getBigBlockSize());
      System.out.println(" BAT (FAT) header blocks: " + header_block.getBATArray().length);
      System.out.println(" BAT (FAT) block count: " + header_block.getBATCount());
      System.out.println(" XBAT (FAT) block count: " + header_block.getXBATCount());
      System.out.println(" XBAT (FAT) block 1 at: " + header_block.getXBATIndex());
      System.out.println(" SBAT (MiniFAT) block count: " + header_block.getSBATCount());
      System.out.println(" SBAT (MiniFAT) block 1 at: " + header_block.getSBATStart());
      System.out.println(" Property table at: " + header_block.getPropertyStart());
      System.out.println("");
	}

   public static void displayRawBlocksSummary(RawDataBlockList data_blocks) throws Exception {
      System.out.println("Raw Blocks Details:");
      System.out.println(" Number of blocks: " + data_blocks.blockCount());
      
      Method gbm = data_blocks.getClass().getSuperclass().getDeclaredMethod("get", int.class);
      gbm.setAccessible(true);
      
      for(int i=0; i<Math.min(16, data_blocks.blockCount()); i++) {
         ListManagedBlock block = (ListManagedBlock)gbm.invoke(data_blocks, Integer.valueOf(i));
         byte[] data = new byte[Math.min(48, block.getData().length)];
         System.arraycopy(block.getData(), 0, data, 0, data.length);
         
         System.out.println(" Block #" + i + ":");
         System.out.println(HexDump.dump(data, 0, 0));
      }
      
      System.out.println("");
   }
   
   public static void displayBATReader(BlockAllocationTableReader batReader) throws Exception {
      System.out.println("Sectors, as referenced from the FAT:");
      Field entriesF = batReader.getClass().getDeclaredField("_entries");
      entriesF.setAccessible(true);
      IntList entries = (IntList)entriesF.get(batReader);
      
      for(int i=0; i<entries.size(); i++) {
         int bn = entries.get(i);
         String bnS = Integer.toString(bn);
         if(bn == POIFSConstants.END_OF_CHAIN) {
            bnS = "End Of Chain";
         } else if(bn == POIFSConstants.DIFAT_SECTOR_BLOCK) {
            bnS = "DI Fat Block";
         } else if(bn == POIFSConstants.FAT_SECTOR_BLOCK) {
            bnS = "Normal Fat Block";
         } else if(bn == POIFSConstants.UNUSED_BLOCK) {
            bnS = "Block Not Used (Free)";
         }
         
         System.out.println("  Block  # " + i + " -> " + bnS);
      }
      
      System.out.println("");
   }
}


File: src/main/java/org/apache/poi/poifs/storage/SmallBlockTableReader.java
/* ====================================================================
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
==================================================================== */

package org.apache.poi.poifs.storage;

import java.io.IOException;

import org.apache.poi.poifs.common.POIFSBigBlockSize;
import org.apache.poi.poifs.property.RootProperty;

/**
 * This class implements reading the small document block list from an
 * existing file
 *
 * @author Marc Johnson (mjohnson at apache dot org)
 */
public final class SmallBlockTableReader {

    /**
     * fetch the small document block list from an existing file
     *
     * @param blockList the raw data from which the small block table
     *                  will be extracted
     * @param root the root property (which contains the start block
     *             and small block table size)
     * @param sbatStart the start block of the SBAT
     *
     * @return the small document block list
     *
     * @exception IOException
     */
    public static BlockList getSmallDocumentBlocks(
            final POIFSBigBlockSize bigBlockSize,
            final RawDataBlockList blockList, final RootProperty root,
            final int sbatStart)
        throws IOException
    {
       // Fetch the blocks which hold the Small Blocks stream
       ListManagedBlock [] smallBlockBlocks = 
          blockList.fetchBlocks(root.getStartBlock(), -1);
        
       // Turn that into a list
       BlockList list =new SmallDocumentBlockList(
             SmallDocumentBlock.extract(bigBlockSize, smallBlockBlocks));

       // Process
        new BlockAllocationTableReader(bigBlockSize,
                                       blockList.fetchBlocks(sbatStart, -1),
                                       list);
        return list;
    }
}


File: src/main/java/org/docx4j/Docx4J.java
/*
   Licensed to Plutext Pty Ltd under one or more contributor license agreements.  
   
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
package org.docx4j;

import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicInteger;

import net.engio.mbassy.bus.MBassador;

import org.docx4j.convert.out.FOSettings;
import org.docx4j.convert.out.HTMLSettings;
import org.docx4j.convert.out.common.Exporter;
import org.docx4j.convert.out.common.preprocess.PartialDeepCopy;
import org.docx4j.convert.out.fo.FOExporterVisitor;
import org.docx4j.convert.out.fo.FOExporterXslt;
import org.docx4j.convert.out.html.HTMLExporterVisitor;
import org.docx4j.convert.out.html.HTMLExporterXslt;
import org.docx4j.events.Docx4jEvent;
import org.docx4j.events.EventFinished;
import org.docx4j.events.PackageIdentifier;
import org.docx4j.events.StartEvent;
import org.docx4j.events.WellKnownJobTypes;
import org.docx4j.events.WellKnownProcessSteps;
import org.docx4j.model.datastorage.BindingHandler;
import org.docx4j.model.datastorage.CustomXmlDataStoragePartSelector;
import org.docx4j.model.datastorage.OpenDoPEHandler;
import org.docx4j.model.datastorage.RemovalHandler;
import org.docx4j.openpackaging.exceptions.Docx4JException;
import org.docx4j.openpackaging.packages.OpcPackage;
import org.docx4j.openpackaging.packages.WordprocessingMLPackage;
import org.docx4j.openpackaging.parts.CustomXmlDataStoragePart;
import org.docx4j.openpackaging.parts.Part;
import org.docx4j.openpackaging.parts.PartName;
import org.docx4j.openpackaging.parts.WordprocessingML.FooterPart;
import org.docx4j.openpackaging.parts.WordprocessingML.HeaderPart;
import org.docx4j.openpackaging.parts.relationships.Namespaces;
import org.docx4j.openpackaging.parts.relationships.RelationshipsPart;
import org.docx4j.relationships.Relationship;
import org.docx4j.utils.TraversalUtilVisitor;
import org.docx4j.wml.SdtElement;
import org.docx4j.wml.SdtPr;
import org.w3c.dom.Document;


/** This is a facade for some typical uses of Docx4J:
 * <ul>
 * <li>Loading a document</li> 
 * <li>Saving a document</li> 
 * <li>Binding xml to content controls in a document</li> 
 * <li>Exporting the document (to HTML, or PDF and other formats supported by the FO renderer) </li> 
 * </ul>
 * 
 */
public class Docx4J {
	
	public static final String MIME_PDF = FOSettings.MIME_PDF;
	public static final String MIME_FO = FOSettings.INTERNAL_FO_MIME;
	
	/** No flags passed, do the default
	 */
	public static final int FLAG_NONE = 0;
	
	/** If available export the document using a xsl transformation
	 */
	public static final int FLAG_EXPORT_PREFER_XSL = 1;
	
	/** If available export the document using a visitor
	 */
	public static final int FLAG_EXPORT_PREFER_NONXSL = 2;

	/** Save the document in a zip container (default docx)
	 */
	public static final int FLAG_SAVE_ZIP_FILE = 1;
	
	/** Save the document as a flat xml document
	 */
	public static final int FLAG_SAVE_FLAT_XML = 2;

	/** inject the passed xml into the document
	 *  if you don't do this step, then the xml in 
	 *  the document will be used.
	 */
	public static final int FLAG_BIND_INSERT_XML = 1;
	
	/** Insert the data of the xml in the content controls 
	 *  Not needed, if the document will only be opened in word 
	 *  and not converted to other formats.
	 */
	public static final int FLAG_BIND_BIND_XML = 2;
	
	/** Remove the content controls of the document
	 */
	public static final int FLAG_BIND_REMOVE_SDT = 4;
	
	/** Remove any xml parts from the document that 
	 *  are used with the content controls.
	 */
	public static final int FLAG_BIND_REMOVE_XML = 8;
	
	private static MBassador<Docx4jEvent> bus;
	public static void setEventNotifier(MBassador<Docx4jEvent> eventbus) {
		bus = eventbus;
	}
	
	protected static class FindContentControlsVisitor extends TraversalUtilVisitor<SdtElement> {
		public static class BreakException extends RuntimeException {
		}
		
		protected Set<String> definedStoreItemIds = null;
		protected String storeItemId = null;
		public FindContentControlsVisitor(Set<String> definedStoreItemIds) {
			this.definedStoreItemIds = definedStoreItemIds;
		}
		
		@Override
		public void apply(SdtElement element) {
		SdtPr sdtPr = element.getSdtPr();
			
			if ((sdtPr.getDataBinding() != null) &&
				(sdtPr.getDataBinding().getStoreItemID() != null)) {
				String tmp = sdtPr.getDataBinding().getStoreItemID().toLowerCase();
				if (definedStoreItemIds.contains(tmp)) {
					storeItemId = tmp;
					throw new BreakException();
				}
			}
		}
		
		public String getdefinedStoreItemId() {
			return storeItemId;
		}
	}
	
	protected static final String NS_CONDITIONS = "http://opendope.org/conditions";
	protected static final String NS_XPATHS = "http://opendope.org/xpaths";
	protected static final String NS_QUESTIONS = "http://opendope.org/questions";
	protected static final String NS_COMPONENTS = "http://opendope.org/components";
	protected static final Set<String> PART_TO_REMOVE_SCHEMA_TYPES = new TreeSet<String>();
	
	static {
		PART_TO_REMOVE_SCHEMA_TYPES.add(NS_CONDITIONS);
		PART_TO_REMOVE_SCHEMA_TYPES.add(NS_XPATHS);
		PART_TO_REMOVE_SCHEMA_TYPES.add(NS_QUESTIONS);
		PART_TO_REMOVE_SCHEMA_TYPES.add(NS_COMPONENTS);
	}


	/**
	 *  Load a Docx Document from a File
	 */	
	public static WordprocessingMLPackage load(File inFile) throws Docx4JException {
		
		return WordprocessingMLPackage.load(inFile);
	}

	/**
	 *  Load a Docx Document from a File, assigning it an identifier for eventing
	 *  
	 *  @since 3.1.0
	 */	
	public static WordprocessingMLPackage load(PackageIdentifier pkgIdentifier, File inFile) throws Docx4JException {
		
		return (WordprocessingMLPackage)OpcPackage.load(pkgIdentifier, inFile);
	}
	
	/**
	 *  Load a Docx Document from an InputStream
	 */	
	public static WordprocessingMLPackage load(InputStream inStream) throws Docx4JException {
		return WordprocessingMLPackage.load(inStream);
	}

	/**
	 *  Load a Docx Document from an InputStream, assigning it an identifier for eventing
	 *  
	 *  @since 3.1.0
	 */	
	public static WordprocessingMLPackage load(PackageIdentifier pkgIdentifier, InputStream inStream) throws Docx4JException {
		return (WordprocessingMLPackage)OpcPackage.load(pkgIdentifier, inStream);
	}
	
	
	/**
	 *  Save a Docx Document to a File
	 */	
	public static void save(WordprocessingMLPackage wmlPackage, File outFile, int flags) throws Docx4JException {
		
		wmlPackage.save(outFile, flags);
	}
	
	/**
	 *  Save a Docx Document to an OutputStream
	 */	
	public static void save(WordprocessingMLPackage wmlPackage, OutputStream outStream, int flags) throws Docx4JException {
		
		wmlPackage.save(outStream, flags);
		
	}
	
	/**
	 *  Bind the content controls of the passed document to the xml.
	 */	
	public static void bind(WordprocessingMLPackage wmlPackage, String xmlDocument, int flags) throws Docx4JException {
		
		ByteArrayInputStream xmlStream = null;
		if (flags == FLAG_NONE) {
			//do everything
			flags = (FLAG_BIND_INSERT_XML |
					 FLAG_BIND_BIND_XML |
					 FLAG_BIND_REMOVE_SDT |
					 FLAG_BIND_REMOVE_XML);
		}
		if ((flags & FLAG_BIND_INSERT_XML) == FLAG_BIND_INSERT_XML) {
			try {
				xmlStream = new ByteArrayInputStream(xmlDocument.getBytes("UTF-8"));
			} catch (UnsupportedEncodingException e1) {
				xmlStream = new ByteArrayInputStream(xmlDocument.getBytes());
			}
		}
        bind(wmlPackage, xmlStream, flags);
	}
	
	/**
	 *  Bind the content controls of the passed document to the xml.
	 */	
	public static void bind(WordprocessingMLPackage wmlPackage, InputStream xmlDocument, int flags) throws Docx4JException {
		
		StartEvent bindJobStartEvent = new StartEvent( WellKnownJobTypes.BIND, wmlPackage );
		bindJobStartEvent.publish();
		
		if (flags == FLAG_NONE) {
			//do everything
			flags = (FLAG_BIND_INSERT_XML |
					 FLAG_BIND_BIND_XML |
					 FLAG_BIND_REMOVE_SDT |
					 FLAG_BIND_REMOVE_XML);
		}
	    Document xmlDoc = null;
		if ((flags & FLAG_BIND_INSERT_XML) == FLAG_BIND_INSERT_XML) {
				try {
		            xmlDoc = XmlUtils.getNewDocumentBuilder().parse(xmlDocument);
				} catch (Exception e) {
					throw new Docx4JException("Problems creating a org.w3c.dom.Document for the passed input stream.", e);
				}
		}
        bind(wmlPackage, xmlDoc, flags);
        
		new EventFinished(bindJobStartEvent).publish();
        
	}
	
	/**
	 *  Bind the content controls of the passed document to the xml.
	 */	
	public static void bind(WordprocessingMLPackage wmlPackage, Document xmlDocument, int flags) throws Docx4JException {
		
		OpenDoPEHandler	openDoPEHandler = null;
		CustomXmlDataStoragePart customXmlDataStoragePart = null;
		RemovalHandler removalHandler = null;
		//String xpathStorageItemId = null;
		
		AtomicInteger bookmarkId = null;

		if (flags == FLAG_NONE) {
			//do everything
			flags = (FLAG_BIND_INSERT_XML |
					 FLAG_BIND_BIND_XML |
					 FLAG_BIND_REMOVE_SDT |
					 FLAG_BIND_REMOVE_XML);
		}
		
		customXmlDataStoragePart 
			= CustomXmlDataStoragePartSelector.getCustomXmlDataStoragePart(wmlPackage);
		if (customXmlDataStoragePart==null) {
			throw new Docx4JException("Couldn't find CustomXmlDataStoragePart! exiting..");
		}
	
		if ((flags & FLAG_BIND_INSERT_XML) == FLAG_BIND_INSERT_XML) {
			
			StartEvent startEvent = new StartEvent( WellKnownJobTypes.BIND, wmlPackage, WellKnownProcessSteps.BIND_INSERT_XML );
			startEvent.publish();
			
			insertXMLData(customXmlDataStoragePart, xmlDocument);
			
			new EventFinished(startEvent).publish();
		}
		if ((flags & FLAG_BIND_BIND_XML) == FLAG_BIND_BIND_XML) {
			
			StartEvent startEvent = new StartEvent( WellKnownJobTypes.BIND, wmlPackage, WellKnownProcessSteps.BIND_BIND_XML );
			startEvent.publish();
			
			// since 3.2.2, OpenDoPEHandler also handles w15 repeatingSection,
			// and does that whether or not we have an XPaths part
			openDoPEHandler = new OpenDoPEHandler(wmlPackage);
			openDoPEHandler.preprocess();
			
			BindingHandler bh = new BindingHandler(wmlPackage);
			bh.setStartingIdForNewBookmarks(openDoPEHandler.getNextBookmarkId());
			bh.applyBindings();
			
			new EventFinished(startEvent).publish();
		}
		if ((flags & FLAG_BIND_REMOVE_SDT) == FLAG_BIND_REMOVE_SDT) {
			
			StartEvent startEvent = new StartEvent( WellKnownJobTypes.BIND, wmlPackage, WellKnownProcessSteps.BIND_REMOVE_SDT );
			startEvent.publish();

			removeSDTs(wmlPackage);
			
			new EventFinished(startEvent).publish();
		}
		if ((flags & FLAG_BIND_REMOVE_XML) == FLAG_BIND_REMOVE_XML) {
			
			StartEvent startEvent = new StartEvent( WellKnownJobTypes.BIND, wmlPackage, WellKnownProcessSteps.BIND_REMOVE_XML );
			startEvent.publish();
			
			removeDefinedCustomXmlParts(wmlPackage, customXmlDataStoragePart);
			
			new EventFinished(startEvent).publish();
		}
	}

	protected static void insertXMLData(CustomXmlDataStoragePart customXmlDataStoragePart, Document xmlDocument) throws Docx4JException {
		
		customXmlDataStoragePart.getData().setDocument(xmlDocument);
	}


	protected static String findXPathStorageItemIdInContentControls(WordprocessingMLPackage wmlPackage) {
	FindContentControlsVisitor visitor = null;
		if ((wmlPackage.getCustomXmlDataStorageParts() != null) && 
			(!wmlPackage.getCustomXmlDataStorageParts().isEmpty())) {
			try {
				visitor = new FindContentControlsVisitor(wmlPackage.getCustomXmlDataStorageParts().keySet());
				TraversalUtil.visit(wmlPackage, false, visitor);
			}
			catch (FindContentControlsVisitor.BreakException be) {//noop
			}
		}
		return (visitor != null ? visitor.getdefinedStoreItemId() : null);
	}

	protected static void removeSDTs(WordprocessingMLPackage wmlPackage)throws Docx4JException {
	RemovalHandler removalHandler;
	removalHandler = new RemovalHandler();
	removalHandler.removeSDTs(wmlPackage.getMainDocumentPart(), RemovalHandler.Quantifier.ALL, (String[])null);
		for (Part part:wmlPackage.getParts().getParts().values()) {
			if (part instanceof HeaderPart) {
				removalHandler.removeSDTs((HeaderPart)part, RemovalHandler.Quantifier.ALL, (String[])null);
			}
			else if (part instanceof FooterPart) {
				removalHandler.removeSDTs((FooterPart)part, RemovalHandler.Quantifier.ALL, (String[])null);
			}
		}
	}

	protected static void removeDefinedCustomXmlParts(WordprocessingMLPackage wmlPackage, CustomXmlDataStoragePart customXmlDataStoragePart) {
	List<PartName> partsToRemove = new ArrayList<PartName>();
	RelationshipsPart relationshipsPart = wmlPackage.getMainDocumentPart().getRelationshipsPart();
	List<Relationship> relationshipsList = ((relationshipsPart != null) && 
										    (relationshipsPart.getRelationships() != null) ?
										    relationshipsPart.getRelationships().getRelationship() : null);
	Part part = null;
		if (relationshipsList != null) {
			for (Relationship relationship : relationshipsList) {
				if (Namespaces.CUSTOM_XML_DATA_STORAGE.equals(relationship.getType())) {
					part = relationshipsPart.getPart(relationship);
					if (part==customXmlDataStoragePart) {
						partsToRemove.add(part.getPartName());
					}
				}
			}
		}
		if (!partsToRemove.isEmpty()) {
			for (int i=0; i<partsToRemove.size(); i++) {
				relationshipsPart.removePart(partsToRemove.get(i));
			}
		}
	}

//	protected static boolean IsPartToRemove(Part part, String xpathStorageItemId) {
//	boolean ret = false;
//	RelationshipsPart relationshipsPart = part.getRelationshipsPart();
//	List<Relationship> relationshipsList = ((relationshipsPart != null) && 
//										    (relationshipsPart.getRelationships() != null) ?
//										    relationshipsPart.getRelationships().getRelationship() : null);
//	
//	CustomXmlDataStoragePropertiesPart propertiesPart = null;
//	DatastoreItem datastoreItem = null;
//		if ((relationshipsList != null) && (!relationshipsList.isEmpty())) {
//			for (Relationship relationship : relationshipsList) {
//				if (Namespaces.CUSTOM_XML_DATA_STORAGE_PROPERTIES.equals(relationship.getType())) {
//					propertiesPart = (CustomXmlDataStoragePropertiesPart)relationshipsPart.getPart(relationship);
//					break;
//				}
//			}
//		}
//		if (propertiesPart != null)  {
//			datastoreItem = propertiesPart.getJaxbElement();
//		}
//		if (datastoreItem != null) {
//			if ((datastoreItem.getItemID() != null) && (datastoreItem.getItemID().length() > 0)) {
//				ret = datastoreItem.getItemID().equals(xpathStorageItemId);
//			}
//			if ((!ret) && 
//				(datastoreItem.getSchemaRefs() != null) && 
//				(datastoreItem.getSchemaRefs().getSchemaRef() != null) &&
//				(!datastoreItem.getSchemaRefs().getSchemaRef().isEmpty())) {
//				for (SchemaRef ref : datastoreItem.getSchemaRefs().getSchemaRef()) {
//					if (PART_TO_REMOVE_SCHEMA_TYPES.contains(ref.getUri())) {
//						ret = true;
//						break;
//					}
//				}
//			}
//		}
//		return ret;
//	}
	
	/**
	 *  Duplicate the document
	 */	
	public static WordprocessingMLPackage clone(WordprocessingMLPackage wmlPackage) throws Docx4JException {
		//Using the PartialDeepCopy is probably faster than serializing and deserializing the complete document.
		return (WordprocessingMLPackage)PartialDeepCopy.process(wmlPackage, null);
	}
	
	/**
	 *  Create the configuration object for conversions that are done via xsl-fo
	 */	
	public static FOSettings createFOSettings() {
		return new FOSettings();
	}
	
	/**
	 *  Convert the document via xsl-fo
	 */	
	public static void toFO(FOSettings settings, OutputStream outputStream, int flags) throws Docx4JException {
		
		Exporter<FOSettings> exporter = getFOExporter(flags);
		exporter.export(settings, outputStream);
	}
	
	/**
	 *  Convenience method to convert the document to PDF
	 */	
	public static void toPDF(WordprocessingMLPackage wmlPackage, OutputStream outputStream) throws Docx4JException {
		
		StartEvent startEvent = new StartEvent( wmlPackage, WellKnownProcessSteps.PDF );
		startEvent.publish();
		
		FOSettings settings = createFOSettings();
		settings.setWmlPackage(wmlPackage);
		settings.setApacheFopMime("application/pdf");
		toFO(settings, outputStream, FLAG_NONE);
		
		new EventFinished(startEvent).publish();
	}
	
	protected static Exporter<FOSettings> getFOExporter(int flags) {
		switch (flags) {
			case FLAG_EXPORT_PREFER_NONXSL:
				return FOExporterVisitor.getInstance();
			case FLAG_EXPORT_PREFER_XSL:
			default:
				return FOExporterXslt.getInstance();
		}
	}

	/**
	 *  Create the configuration object for conversions to html
	 */	
	public static HTMLSettings createHTMLSettings() {
		return new HTMLSettings();
	}
	
	/**
	 *  Convert the document to HTML
	 */	
	public static void toHTML(HTMLSettings settings, OutputStream outputStream, int flags) throws Docx4JException {

		StartEvent startEvent = new StartEvent( settings.getWmlPackage(), WellKnownProcessSteps.HTML_OUT );
		startEvent.publish();
		
		Exporter<HTMLSettings> exporter = getHTMLExporter(flags);
		exporter.export(settings, outputStream);
		
		new EventFinished(startEvent).publish();
	}
	
	/**
	 *  Convert the document to HTML
	 */	
	public static void toHTML(WordprocessingMLPackage wmlPackage, String imageDirPath, String imageTargetUri, OutputStream outputStream) throws Docx4JException {

		StartEvent startEvent = new StartEvent( wmlPackage, WellKnownProcessSteps.HTML_OUT );
		startEvent.publish();
		
		HTMLSettings settings = createHTMLSettings();
		settings.setWmlPackage(wmlPackage);
		if (imageDirPath != null) {
			settings.setImageDirPath(imageDirPath);
		}
		if (imageTargetUri != null) {
			settings.setImageTargetUri(imageTargetUri);
		}
		toHTML(settings, outputStream, FLAG_NONE);
		
		new EventFinished(startEvent).publish();
	}
	
	protected static Exporter<HTMLSettings> getHTMLExporter(int flags) {
		switch (flags) {
			case FLAG_EXPORT_PREFER_NONXSL:
				return HTMLExporterVisitor.getInstance();
			case FLAG_EXPORT_PREFER_XSL:
			default:
				return HTMLExporterXslt.getInstance();
		}
	}
}


File: src/main/java/org/docx4j/jaxb/Context.java
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
package org.docx4j.jaxb;


import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.util.Enumeration;
import java.util.jar.Attributes;
import java.util.jar.JarFile;
import java.util.jar.Manifest;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBException;

import org.apache.commons.io.IOUtils;
import org.docx4j.utils.ResourceUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Context {
	
	public static final JAXBContext jc;
	
	// TEMP/Experimental
//	public static void setJc(JAXBContext jc) {
//		Context.jc = jc;
//	}

	@Deprecated
	public static JAXBContext jcThemePart;
	
	public static JAXBContext jcDocPropsCore;
	public static JAXBContext jcDocPropsCustom;
	public static JAXBContext jcDocPropsExtended;
	public static JAXBContext jcRelationships;
	public static JAXBContext jcCustomXmlProperties;
	public static JAXBContext jcContentTypes;

	public static JAXBContext jcXmlPackage;
	
	private static JAXBContext jcXslFo;
	public static JAXBContext jcSectionModel;

	public static JAXBContext jcXmlDSig;

	/** @since 3.0.1 */
	public static JAXBContext jcMCE;
	
	private static Logger log = LoggerFactory.getLogger(Context.class);
		
	static {
		JAXBContext tempContext = null;

		// Display diagnostic info about version of JAXB being used.
		log.info("java.vendor="+System.getProperty("java.vendor"));
		log.info("java.version="+System.getProperty("java.version"));
		
		// This stuff is just debugging diagnostics
		try {
			searchManifestsForJAXBImplementationInfo( ClassLoader.getSystemClassLoader());
			if (Thread.currentThread().getContextClassLoader()==null) {
				log.warn("ContextClassLoader is null for current thread");
				// Happens with IKVM 
			} else if (ClassLoader.getSystemClassLoader()!=Thread.currentThread().getContextClassLoader()) {
				searchManifestsForJAXBImplementationInfo(Thread.currentThread().getContextClassLoader());
			}
		} catch ( java.security.AccessControlException e) {
			// Google AppEngine throws this, at com.google.apphosting.runtime.security.CustomSecurityManager.checkPermission
			log.warn("Caught/ignored " + e.getMessage());
		}
		
		// Diagnostics regarding JAXB implementation
		InputStream jaxbPropsIS=null;
		try {
			// Is MOXy configured?
			jaxbPropsIS = ResourceUtils.getResource("org/docx4j/wml/jaxb.properties");
			log.info("MOXy JAXB implementation intended..");
		} catch (Exception e3) {
			log.info("No MOXy JAXB config found; assume not intended..");
			log.debug(e3.getMessage());
		}
		if (jaxbPropsIS==null) {
			// Only probe for other implementations if no MOXy
			try {
				Object namespacePrefixMapper = NamespacePrefixMapperUtils.getPrefixMapper();
				if ( namespacePrefixMapper.getClass().getName().equals("org.docx4j.jaxb.NamespacePrefixMapperSunInternal") ) {
					// Java 6
					log.info("Using Java 6/7 JAXB implementation");
				} else {
					log.info("Using JAXB Reference Implementation");			
				}
				
			} catch (JAXBException e) {
				log.error("PANIC! No suitable JAXB implementation available");
				log.error(e.getMessage(), e);
				e.printStackTrace();
			}
		}
      
      try { 
			// JAXBContext.newInstance uses the context class loader of the current thread. 
			// To specify the use of a different class loader, 
			// either set it via the Thread.setContextClassLoader() api 
			// or use the newInstance method.
			// JBOSS (older versions only?) might use a different class loader to load JAXBContext, 
    	  	// which caused problems, so in docx4j we explicitly specify our class loader.  
    	  	// IKVM 7.3.4830 also needs this to be done
    	  	// (java.lang.Thread.currentThread().setContextClassLoader doesn't seem to help!)
    	  	// and there are no environments in which this approach is known to be problematic
			
			java.lang.ClassLoader classLoader = Context.class.getClassLoader();

			tempContext = JAXBContext.newInstance("org.docx4j.wml:org.docx4j.w14:org.docx4j.w15:" +
					"org.docx4j.schemas.microsoft.com.office.word_2006.wordml:" +
					"org.docx4j.dml:org.docx4j.dml.chart:org.docx4j.dml.chartDrawing:org.docx4j.dml.compatibility:org.docx4j.dml.diagram:org.docx4j.dml.lockedCanvas:org.docx4j.dml.picture:org.docx4j.dml.wordprocessingDrawing:org.docx4j.dml.spreadsheetdrawing:org.docx4j.dml.diagram2008:" +
					// All VML stuff is here, since compiling it requires WML and DML (and MathML), but not PML or SML
					"org.docx4j.vml:org.docx4j.vml.officedrawing:org.docx4j.vml.wordprocessingDrawing:org.docx4j.vml.presentationDrawing:org.docx4j.vml.spreadsheetDrawing:org.docx4j.vml.root:" +
					"org.docx4j.docProps.coverPageProps:" +
					"org.opendope.xpaths:org.opendope.conditions:org.opendope.questions:org.opendope.answers:org.opendope.components:org.opendope.SmartArt.dataHierarchy:" +
					"org.docx4j.math:" +
					"org.docx4j.sharedtypes:org.docx4j.bibliography",classLoader );
			
			if (tempContext.getClass().getName().equals("org.eclipse.persistence.jaxb.JAXBContext")) {
				log.info("MOXy JAXB implementation is in use!");
			} else {
				log.info("Not using MOXy; using " + tempContext.getClass().getName());				
			}
			
			jcThemePart = tempContext; //JAXBContext.newInstance("org.docx4j.dml",classLoader );
			jcDocPropsCore = JAXBContext.newInstance("org.docx4j.docProps.core:org.docx4j.docProps.core.dc.elements:org.docx4j.docProps.core.dc.terms",classLoader );
			jcDocPropsCustom = JAXBContext.newInstance("org.docx4j.docProps.custom",classLoader );
			jcDocPropsExtended = JAXBContext.newInstance("org.docx4j.docProps.extended",classLoader );
			jcXmlPackage = JAXBContext.newInstance("org.docx4j.xmlPackage",classLoader );
			jcRelationships = JAXBContext.newInstance("org.docx4j.relationships",classLoader );
			jcCustomXmlProperties = JAXBContext.newInstance("org.docx4j.customXmlProperties",classLoader );
			jcContentTypes = JAXBContext.newInstance("org.docx4j.openpackaging.contenttype",classLoader );
			
			jcSectionModel = JAXBContext.newInstance("org.docx4j.model.structure.jaxb",classLoader );
			
			jcXmlDSig = JAXBContext.newInstance("org.plutext.jaxb.xmldsig",classLoader );

			jcMCE = JAXBContext.newInstance("org.docx4j.mce",classLoader );
			
			log.debug(".. other contexts loaded ..");
										
			
		} catch (Exception ex) {
			log.error("Cannot initialize context", ex);
		}				
      jc = tempContext;
	}
	
	private static org.docx4j.wml.ObjectFactory wmlObjectFactory;
	
	public static org.docx4j.wml.ObjectFactory getWmlObjectFactory() {
		
		if (wmlObjectFactory==null) {
			wmlObjectFactory = new org.docx4j.wml.ObjectFactory();
		}
		return wmlObjectFactory;
		
	}

	public static JAXBContext getXslFoContext() {
		if (jcXslFo==null) {
			try {	
				Context tmp = new Context();
				java.lang.ClassLoader classLoader = tmp.getClass().getClassLoader();

				jcXslFo = JAXBContext.newInstance("org.plutext.jaxb.xslfo",classLoader );
				
			} catch (JAXBException ex) {
	      log.error("Cannot determine XSL-FO context", ex);
			}						
		}
		return jcXslFo;		
	}
	
	public static void searchManifestsForJAXBImplementationInfo(ClassLoader loader) {
	    Enumeration resEnum;
	    try {
	        resEnum = loader.getResources(JarFile.MANIFEST_NAME);
	        while (resEnum.hasMoreElements()) {
	        	InputStream is = null;
	            try {
	                URL url = (URL)resEnum.nextElement();
//	                System.out.println("\n\n" + url);
	                is = url.openStream();
	                if (is != null) {
	                    Manifest manifest = new Manifest(is);

                    	Attributes mainAttribs = manifest.getMainAttributes();
                    	String impTitle = mainAttribs.getValue("Implementation-Title");
                    	if (impTitle!=null
                    			&& impTitle.contains("JAXB Reference Implementation")
                    					|| impTitle.contains("org.eclipse.persistence") ) {
	                    
        	                log.info("\n" + url);
		                    for(Object key2  : mainAttribs.keySet() ) {
		                    	
		                    	log.info(key2 + " : " + mainAttribs.getValue((java.util.jar.Attributes.Name)key2));
		                    }
                    	}
                    	
	                    // In 2.1.3, it is in here
	                    for(String key  :  manifest.getEntries().keySet() ) {
	    	                //System.out.println(key);	                    
	    	                if (key.equals("com.sun.xml.bind.v2.runtime")) {
		    	                log.info("Found JAXB reference implementation in " + url);
		                    	mainAttribs = manifest.getAttributes((String)key);
		                    
			                    for(Object key2  : mainAttribs.keySet() ) {
			                    	log.info(key2 + " : " + mainAttribs.getValue((java.util.jar.Attributes.Name)key2));
			                    }
		                    }
	                    }
	                    
	                }
	            }
	            catch (Exception e) {
	                // Silently ignore 
//	            	log.error(e.getMessage(), e);
	            } finally {
	            	IOUtils.closeQuietly(is);
	            }
	        }
	    } catch (IOException e1) {
	        // Silently ignore 
//        	log.error(e1);
	    }
	     
	}	
}


File: src/main/java/org/docx4j/openpackaging/packages/OpcPackage.java
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

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.StringWriter;
import java.util.HashMap;

import javax.xml.bind.JAXBContext;
import javax.xml.bind.JAXBElement;
import javax.xml.bind.JAXBException;
import javax.xml.bind.Marshaller;

import org.apache.poi.poifs.crypt.Decryptor;
import org.apache.poi.poifs.crypt.EncryptionInfo;
import org.apache.poi.poifs.filesystem.POIFSFileSystem;
import org.docx4j.Docx4J;
import org.docx4j.TextUtils;
import org.docx4j.convert.in.FlatOpcXmlImporter;
import org.docx4j.convert.out.flatOpcXml.FlatOpcXmlCreator;
import org.docx4j.docProps.core.dc.elements.SimpleLiteral;
import org.docx4j.events.EventFinished;
import org.docx4j.events.PackageIdentifier;
import org.docx4j.events.PackageIdentifierTransient;
import org.docx4j.events.StartEvent;
import org.docx4j.events.WellKnownProcessSteps;
import org.docx4j.jaxb.Context;
import org.docx4j.jaxb.NamespacePrefixMapperUtils;
import org.docx4j.openpackaging.Base;
import org.docx4j.openpackaging.contenttype.ContentTypeManager;
import org.docx4j.openpackaging.exceptions.Docx4JException;
import org.docx4j.openpackaging.exceptions.InvalidFormatException;
import org.docx4j.openpackaging.io.LoadFromZipNG;
import org.docx4j.openpackaging.io.SaveToZipFile;
import org.docx4j.openpackaging.io3.Load3;
import org.docx4j.openpackaging.io3.Save;
import org.docx4j.openpackaging.io3.stores.PartStore;
import org.docx4j.openpackaging.io3.stores.ZipPartStore;
import org.docx4j.openpackaging.parts.CustomXmlPart;
import org.docx4j.openpackaging.parts.DocPropsCorePart;
import org.docx4j.openpackaging.parts.DocPropsCustomPart;
import org.docx4j.openpackaging.parts.DocPropsExtendedPart;
import org.docx4j.openpackaging.parts.ExternalTarget;
import org.docx4j.openpackaging.parts.Part;
import org.docx4j.openpackaging.parts.PartName;
import org.docx4j.openpackaging.parts.Parts;
import org.docx4j.openpackaging.parts.relationships.Namespaces;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;


/**
 * Represent a Package as defined in the Open Packaging Specification.
 * 
 * @author Jason Harrop
 */
public class OpcPackage extends Base implements PackageIdentifier {

	private static Logger log = LoggerFactory.getLogger(OpcPackage.class);

	/**
	 * This HashMap is intended to prevent loops during the loading 
	 * of this package. TODO This doesn't really tell us anything that
	 * the contents of Parts couldn't also tell us (except that
	 * that doesn't contain the rels parts), so consider removing.
	 * At least replace it with a method, so this implementation
	 * detail is hidden!
	 */
	public HashMap<String, String> handled = new HashMap<String, String>();
	
	/**
	 * Package parts collection.  This is a collection of _all_
	 * parts in the package (_except_ relationship parts), 
	 * not just those referred to by the package-level relationships.
	 * It doesn't include external resources.
	 */
	protected Parts parts = new Parts();

	/**
	 * Retrieve the Parts object.
	 */
	public Parts getParts() {

		// Having a separate Parts object doesn't really buy
		// us much, but live with it...
		
		return parts;		
	}
	
	// Currently only external images are stored here
	protected HashMap<ExternalTarget, Part> externalResources 
		= new HashMap<ExternalTarget, Part>();
	public HashMap<ExternalTarget, Part> getExternalResources() {
		return externalResources;		
	}	
	
	protected HashMap<String, CustomXmlPart> customXmlDataStorageParts
		= new HashMap<String, CustomXmlPart>(); // NB key is lowercase
	/**
	 * keyed by item id (in lower case)
	 * @return
	 */
	public HashMap<String, CustomXmlPart> getCustomXmlDataStorageParts() {
		return customXmlDataStorageParts;
	}	
	
	protected ContentTypeManager contentTypeManager;

	public ContentTypeManager getContentTypeManager() {
		return contentTypeManager;
	}

	public void setContentTypeManager(ContentTypeManager contentTypeManager) {
		this.contentTypeManager = contentTypeManager;
	}
	
	private PartStore sourcePartStore;	
	
	/**
	 * @return the partStore
	 * @since 3.0.
	 */
	public PartStore getSourcePartStore() {
		return sourcePartStore;
	}

	/**
	 * @param partStore the partStore to set
	 * @since 3.0.
	 */
	public void setSourcePartStore(PartStore partStore) {
		this.sourcePartStore = partStore;
	}

	private PartStore targetPartStore;	
	
	/**
	 * @return the partStore
	 * @since 3.0.
	 */
	public PartStore getTargetPartStore() {
		return targetPartStore;
	}

	/**
	 * @param partStore the partStore to set
	 * @since 3.0.
	 */
	public void setTargetPartStore(PartStore partStore) {
		this.targetPartStore = partStore;
	}
	
	/**
	 * Constructor.  Also creates a new content type manager
	 * 
	 */
	public OpcPackage() {
		try {
			this.setPartName(new PartName("/", false));
			
			contentTypeManager = new ContentTypeManager();
		} catch (Exception e) {
			log.error(e.getMessage());
			// TODO: handle exception
		}
	}

	/**
	 * Constructor.
	 *  
	 * @param contentTypeManager
	 *            The content type manager to use 
	 */
	public OpcPackage(ContentTypeManager contentTypeManager) {
		try {
			this.setPartName(new PartName("/", false));
			
			this.contentTypeManager = contentTypeManager;
		} catch (Exception e) {
			log.error(e.getMessage());
			// TODO: handle exception
		}
	}
	
	public OpcPackage getPackage() {
		return this;
	}
		
	
	protected DocPropsCorePart docPropsCorePart;

	protected DocPropsExtendedPart docPropsExtendedPart;
	
	protected DocPropsCustomPart docPropsCustomPart;
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an existing File (.docx/.docxm, .ppxtx or Flat OPC .xml).
     *
	 * @param docxFile
	 *            The docx file 
	 * @since 3.1.0
	 */	
	public static OpcPackage load(PackageIdentifier pkgIdentifier, final java.io.File docxFile) throws Docx4JException {
		return load(pkgIdentifier, docxFile, null);
	}
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an existing File (.docx/.docxm, .ppxtx or Flat OPC .xml).
     *
	 * @param docxFile
	 *            The docx file 
	 */	
	public static OpcPackage load(final java.io.File docxFile) throws Docx4JException {
		return load(docxFile, null);
	}
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an existing File (.docx/.docxm, .ppxtx or Flat OPC .xml).
     *
	 * @param docxFile
	 *            The docx file
	 * @param password
	 *            The password, if the file is password protected (compound)
	 *            
	 * @Since 2.8.0           
	 */	
	public static OpcPackage load(final java.io.File docxFile, String password) throws Docx4JException {
		
		PackageIdentifier name = new PackageIdentifierTransient(docxFile.getName());
		
		try {
			return OpcPackage.load(name, new FileInputStream(docxFile), password );
		} catch (final FileNotFoundException e) {
			OpcPackage.log.error(e.getMessage(), e);
			throw new Docx4JException("Couldn't load file from " + docxFile.getAbsolutePath(), e);
		}
	}

	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an existing File (.docx/.docxm, .ppxtx or Flat OPC .xml).
     *
	 * @param docxFile
	 *            The docx file
	 * @param password
	 *            The password, if the file is password protected (compound)
	 *            
	 * @Since 3.1.0         
	 */	
	public static OpcPackage load(PackageIdentifier pkgIdentifier, final java.io.File docxFile, String password) throws Docx4JException {
		
		try {
			return OpcPackage.load(pkgIdentifier, new FileInputStream(docxFile), password );
		} catch (final FileNotFoundException e) {
			OpcPackage.log.error(e.getMessage(), e);
			throw new Docx4JException("Couldn't load file from " + docxFile.getAbsolutePath(), e);
		}
	}
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * It detects the convenient format inspecting two first bytes of stream (magic bytes). 
	 * For office 2007 'x' formats, these two bytes are 'PK' (same as zip file)  
     *
	 * @param inputStream
	 *            The docx file 
	 */	
	public static OpcPackage load(final InputStream inputStream) throws Docx4JException {
		return load(inputStream, "");
	}

	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * It detects the convenient format inspecting two first bytes of stream (magic bytes). 
	 * For office 2007 'x' formats, these two bytes are 'PK' (same as zip file)  
     *
	 * @param inputStream
	 *            The docx file 
	 *            
	 * @since 3.1.0            
	 */	
	public static OpcPackage load(PackageIdentifier pkgIdentifier, final InputStream inputStream) throws Docx4JException {
		return load(pkgIdentifier, inputStream, "");
	}
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * It detects the convenient format inspecting two first bytes of stream (magic bytes). 
	 * For office 2007 'x' formats, these two bytes are 'PK' (same as zip file)  
     *
	 * @param inputStream
	 *            The docx file 
	 * @param password
	 *            The password, if the file is password protected (compound)
	 *            
	 * @Since 2.8.0           
	 */	
	public static OpcPackage load(final InputStream inputStream, String password) throws Docx4JException {

		return load(null, inputStream,  password);
	}
	
	/**
	 * Convenience method to create a WordprocessingMLPackage
	 * or PresentationMLPackage
	 * from an inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * It detects the convenient format inspecting two first bytes of stream (magic bytes). 
	 * For office 2007 'x' formats, these two bytes are 'PK' (same as zip file)  
     *
	 * @param inputStream
	 *            The docx file 
	 * @param password
	 *            The password, if the file is password protected (compound)
	 *            
	 * @Since 3.1.0     
	 */	
	private static OpcPackage load(PackageIdentifier pkgIdentifier, final InputStream inputStream, String password) throws Docx4JException {
		
		//try to detect the type of file using a bufferedinputstream
		final BufferedInputStream bis = new BufferedInputStream(inputStream);
		bis.mark(0);
		final byte[] firstTwobytes=new byte[2];
		int read=0;
		try {
			read = bis.read(firstTwobytes);
			bis.reset();
		} catch (final IOException e) {
			throw new Docx4JException("Error reading from the stream", e);
		}
		if (read!=2){
			throw new Docx4JException("Error reading from the stream (no bytes available)");
		}
		if (firstTwobytes[0]=='P' && firstTwobytes[1]=='K') { // 50 4B
			return OpcPackage.load(pkgIdentifier, bis, Filetype.ZippedPackage, null);
		} else if  (firstTwobytes[0]==(byte)0xD0 && firstTwobytes[1]==(byte)0xCF) {
			// password protected docx is a compound file, with signature D0 CF 11 E0 A1 B1 1A E1
			log.info("Detected compound file");
			return OpcPackage.load(pkgIdentifier, bis, Filetype.Compound, password);
		} else {
			//Assume..
			log.info("Assuming Flat OPC XML");
			return OpcPackage.load(pkgIdentifier, bis, Filetype.FlatOPC, null);
		}
	}
	
	
	/**
	 * convenience method to load a word2007 document 
	 * from an existing inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * Included for backwards compatibility
	 * 
	 * @param is
	 * @param docxFormat
	 * @return
	 * @throws Docx4JException
	 */
	@Deprecated
	public static OpcPackage load(final InputStream is, final boolean docxFormat) throws Docx4JException {
		return load(is);  // check again, in case its a password protected compound file
	}

	/**
	 * convenience method to load a word2007 document 
	 * from an existing inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * 
	 * @param is
	 * @param docxFormat
	 * @return
	 * @throws Docx4JException
	 * 
	 * @Since 2.8.0           
	 */
	public static OpcPackage load(final InputStream is, Filetype type) throws Docx4JException {
		return load(is, type, null);
	}

	/**
	 * convenience method to load a word2007 document 
	 * from an existing inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * 
	 * @param is
	 * @param docxFormat
	 * @return
	 * @throws Docx4JException
	 * 
	 * @Since 2.8.0           
	 */
	public static OpcPackage load(final InputStream is, Filetype type, String password) throws Docx4JException {

		return load(null, is, type, password);
	}
	
	/**
	 * convenience method to load a word2007 document 
	 * from an existing inputstream (.docx/.docxm, .ppxtx or Flat OPC .xml).
	 * 
	 * @param is
	 * @param docxFormat
	 * @return
	 * @throws Docx4JException
	 * 
	 * @Since 3.1.0      
	 */
	private static OpcPackage load(PackageIdentifier pkgIdentifier, final InputStream is, Filetype type, String password) throws Docx4JException {

		if (pkgIdentifier==null) {
			pkgIdentifier = new PackageIdentifierTransient("pkg_" + System.currentTimeMillis());
		}
		
		StartEvent startEvent = new StartEvent( pkgIdentifier,  WellKnownProcessSteps.PKG_LOAD );
		startEvent.publish();			
		
		if (type.equals(Filetype.ZippedPackage)){
			
			final ZipPartStore partLoader = new ZipPartStore(is);
			final Load3 loader = new Load3(partLoader);
			OpcPackage opcPackage = loader.get();
			
			if (pkgIdentifier!=null) {
				opcPackage.setName(pkgIdentifier.name());
			}
			
			new EventFinished(startEvent).publish();						
			return opcPackage;
			
//			final LoadFromZipNG loader = new LoadFromZipNG();
//			return loader.get(is);			
			
		} else if (type.equals(Filetype.Compound)){
			
	        try {
				POIFSFileSystem fs = new POIFSFileSystem(is);
				EncryptionInfo info = new EncryptionInfo(fs); 
		        Decryptor d = Decryptor.getInstance(info); 
		        d.verifyPassword(password); 
		        
				InputStream is2 = d.getDataStream(fs);
				final LoadFromZipNG loader = new LoadFromZipNG();
				return loader.get(is2);				
				
			} catch (java.security.InvalidKeyException e) {
		        /* Wrong password results in:
		         * 
			        Caused by: java.security.InvalidKeyException: No installed provider supports this key: (null)
			    	at javax.crypto.Cipher.a(DashoA13*..)
			    	at javax.crypto.Cipher.init(DashoA13*..)
			    	at javax.crypto.Cipher.init(DashoA13*..)
			    	at org.apache.poi.poifs.crypt.AgileDecryptor.getCipher(AgileDecryptor.java:216)
			    	at org.apache.poi.poifs.crypt.AgileDecryptor.access$200(AgileDecryptor.java:39)
			    	at org.apache.poi.poifs.crypt.AgileDecryptor$ChunkedCipherInputStream.<init>(AgileDecryptor.java:127)
			    	at org.apache.poi.poifs.crypt.AgileDecryptor.getDataStream(AgileDecryptor.java:103)
			    	at org.apache.poi.poifs.crypt.Decryptor.getDataStream(Decryptor.java:85)		        
		         */
				throw new Docx4JException("Problem reading compound file: wrong password?", e);
			} catch (Exception e) {
				throw new Docx4JException("Problem reading compound file", e);
			} finally {
				new EventFinished(startEvent).publish();				
			}
		}
		
		try {
			FlatOpcXmlImporter xmlPackage = new FlatOpcXmlImporter(is); 
			return xmlPackage.get(); 
		} catch (final Exception e) {
			OpcPackage.log.error(e.getMessage(), e);
			throw new Docx4JException("Couldn't load xml from stream ",e);
		} finally {
			new EventFinished(startEvent).publish();									
		}
	}

	/**
	 * Convenience method to save a WordprocessingMLPackage
	 * or PresentationMLPackage to a File.  If the file ends with .xml,
	 * use Flat OPC XML format; otherwise zip it up.
	 */	
	public void save(java.io.File file) throws Docx4JException {
		if (file.getName().endsWith(".xml")) {
			save(file, Docx4J.FLAG_SAVE_FLAT_XML);			
		} else {
			save(file, Docx4J.FLAG_SAVE_ZIP_FILE);						
		}
	}	

	// TODO: support for writing password protected files 
	
//			// Create the compound file
//	        try {
//	        	// Write the package to a stream
//	        	
//	        	// .. then encrypt
//	        	
//	        	// TODO.  See for example http://code.google.com/p/ooxmlcrypto/source/browse/trunk/OfficeCrypto/OfficeCrypto.cs
//				

	
	/**
	 *  Save this pkg to a File. The flag is typically Docx4J.FLAG_SAVE_ZIP_FILE
	 *  or Docx4J.FLAG_SAVE_FLAT_XML
	 *  
	 *  @since 3.1.0
	 */	
	public void save(File outFile, int flags) throws Docx4JException {
		
		OutputStream outStream = null;
		try {
			outStream = new FileOutputStream(outFile);
			save(outStream, flags);
		} catch (FileNotFoundException e) {
			throw new Docx4JException("Exception creating output stream: " + e.getMessage(), e);
		}
		finally {
			if (outStream != null) {
				try {
					outStream.close();
				} catch (IOException e) {}
				outStream = null;
			}
		}
		
	}	

	/**
	 *  Save this pkg to an OutputStream in the usual zipped up format
	 *  (Docx4J.FLAG_SAVE_ZIP_FILE)
	 *  
	 *  @since 3.1.0
	 */	
	public void save(OutputStream outStream) throws Docx4JException {
		save(outStream, Docx4J.FLAG_SAVE_ZIP_FILE);						
	}

	
	/**
	 *  Save this pkg to an OutputStream. The flag is typically Docx4J.FLAG_SAVE_ZIP_FILE
	 *  or Docx4J.FLAG_SAVE_FLAT_XML
	 *  
	 *  @since 3.1.0
	 */	
	public void save(OutputStream outStream, int flags) throws Docx4JException {
		
		StartEvent startEvent = new StartEvent( this,  WellKnownProcessSteps.PKG_SAVE );
		startEvent.publish();
		
		if (flags == Docx4J.FLAG_SAVE_FLAT_XML) {
			JAXBContext jc = Context.jcXmlPackage;
			FlatOpcXmlCreator opcXmlCreator = new FlatOpcXmlCreator(this);
			org.docx4j.xmlPackage.Package pkg = opcXmlCreator.get();
			Marshaller marshaller;
			try {
				marshaller = jc.createMarshaller();
				NamespacePrefixMapperUtils.setProperty(marshaller, 
						NamespacePrefixMapperUtils.getPrefixMapper());			
				marshaller.marshal(pkg, outStream);				
			} catch (JAXBException e) {
				throw new Docx4JException("Exception marshalling document for output: " + e.getMessage(), e);
			}
		}
		else {
//			SaveToZipFile saver = new SaveToZipFile(wmlPackage);
			Save saver = new Save(this);
			saver.save(outStream);
		}
		new EventFinished(startEvent).publish();
	}	
	
	
	

	@Override
	public boolean setPartShortcut(Part part, String relationshipType) {
		if (relationshipType.equals(Namespaces.PROPERTIES_CORE)) {
			docPropsCorePart = (DocPropsCorePart)part;
			return true;			
		} else if (relationshipType.equals(Namespaces.PROPERTIES_CUSTOM)) {
			docPropsCustomPart = (DocPropsCustomPart)part;
			return true;			
		} else if (relationshipType.equals(Namespaces.PROPERTIES_EXTENDED)) {
			docPropsExtendedPart = (DocPropsExtendedPart)part;
			return true;			
		} else {	
			return false;
		}
	}

	public DocPropsCorePart getDocPropsCorePart() {
//		if (docPropsCorePart==null) {
//			try {
//				docPropsCorePart = new org.docx4j.openpackaging.parts.DocPropsCorePart();
//				this.addTargetPart(docPropsCorePart);
//				
//				org.docx4j.docProps.core.ObjectFactory factory = 
//					new org.docx4j.docProps.core.ObjectFactory();				
//				org.docx4j.docProps.core.CoreProperties properties = factory.createCoreProperties();
//				((org.docx4j.openpackaging.parts.JaxbXmlPart)docPropsCorePart).setJaxbElement((Object)properties);
//				((org.docx4j.openpackaging.parts.JaxbXmlPart)docPropsCorePart).setJAXBContext(Context.jcDocPropsCore);						
//			} catch (InvalidFormatException e) {
//				// TODO Auto-generated catch block
//				e.printStackTrace();
//			}			
//		}
		return docPropsCorePart;
	}

	public DocPropsExtendedPart getDocPropsExtendedPart() {
//		if (docPropsExtendedPart==null) {
//			try {
//				docPropsExtendedPart = new org.docx4j.openpackaging.parts.DocPropsExtendedPart();
//				this.addTargetPart(docPropsExtendedPart);
//				
//				org.docx4j.docProps.extended.ObjectFactory factory = 
//					new org.docx4j.docProps.extended.ObjectFactory();				
//				org.docx4j.docProps.extended.Properties properties = factory.createProperties();
//				((org.docx4j.openpackaging.parts.JaxbXmlPart)docPropsExtendedPart).setJaxbElement((Object)properties);
//				((org.docx4j.openpackaging.parts.JaxbXmlPart)docPropsExtendedPart).setJAXBContext(Context.jcDocPropsExtended);										
//			} catch (InvalidFormatException e) {
//				// TODO Auto-generated catch block
//				e.printStackTrace();
//			}			
//		}
		return docPropsExtendedPart;
	}

	/**
	 * Get DocPropsCustomPart, if any.
	 * 
	 * @return
	 */
	public DocPropsCustomPart getDocPropsCustomPart() {
		
//		if (docPropsCustomPart==null) {
//			try {
//				docPropsCustomPart = new org.docx4j.openpackaging.parts.DocPropsCustomPart();
//				this.addTargetPart(docPropsCustomPart);
//				
//				org.docx4j.docProps.custom.ObjectFactory factory = 
//					new org.docx4j.docProps.custom.ObjectFactory();
//				
//				org.docx4j.docProps.custom.Properties properties = factory.createProperties();
//				((org.docx4j.openpackaging.parts.JaxbXmlPart)docPropsCustomPart).setJaxbElement((Object)properties);
//
//				((org.docx4j.openpackaging.parts.JaxbXmlPart)docPropsCustomPart).setJAXBContext(Context.jcDocPropsCustom);										
//				
//			} catch (InvalidFormatException e) {
//				// TODO Auto-generated catch block
//				e.printStackTrace();
//			}			
//		}
		
		return docPropsCustomPart;
	}
	
	/**
	 * @since 3.0.0
	 */	
	public void setTitle(String title) {
		
		if (this.getDocPropsCorePart()==null) {
			DocPropsCorePart core;
			try {
				core = new DocPropsCorePart();
				org.docx4j.docProps.core.ObjectFactory coreFactory = new org.docx4j.docProps.core.ObjectFactory();
				core.setJaxbElement(coreFactory.createCoreProperties() );
				this.addTargetPart(core);			
			} catch (InvalidFormatException e) {
				log.error(e.getMessage(), e);
			}
		}
		
		org.docx4j.docProps.core.dc.elements.ObjectFactory of = new org.docx4j.docProps.core.dc.elements.ObjectFactory();
		SimpleLiteral literal = of.createSimpleLiteral();
		literal.getContent().add(title);
		this.getDocPropsCorePart().getJaxbElement().setTitle(of.createTitle(literal) );				
	}
	
	/**
	 * @since 3.0.0
	 */	
	public String getTitle() {
		
		if (this.getDocPropsCorePart()==null) {
			return null;
		}
		
		JAXBElement<SimpleLiteral> sl = this.getDocPropsCorePart().getJaxbElement().getTitle();
		if (sl == null) return null;
		
		StringWriter sw = new StringWriter(); 
		 try {
			TextUtils.extractText(sl, sw, Context.jcDocPropsCore);
		} catch (Exception e) {
			log.error(e.getMessage(), e);
		}
		return sw.toString();				
	}
	

	/** @since 2.7.2 */
	public OpcPackage clone() {
		
		OpcPackage result = null;
		
		// Zip it up
		ByteArrayOutputStream baos = new ByteArrayOutputStream();
		SaveToZipFile saver = new SaveToZipFile(this);
		try {
			saver.save(baos);
			result = load(new ByteArrayInputStream(baos.toByteArray()));
		} catch (Docx4JException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}

		return result;
		
	}

	@Override
	public String name() {
		return name;
	}
	private String name;
	/**
	 * Allocate a name to this package, for the purposes of Docx4jEvent,
	 * and logging.
	 */
	public void setName(String name) {
		this.name = name;
	}
	
}


File: src/main/java/org/docx4j/openpackaging/parts/WordprocessingML/OleObjectBinaryPart.java
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

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.util.Iterator;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.apache.poi.poifs.dev.POIFSViewEngine;
import org.apache.poi.poifs.filesystem.DirectoryNode;
import org.apache.poi.poifs.filesystem.DocumentNode;
import org.apache.poi.poifs.filesystem.Entry;
import org.apache.poi.poifs.filesystem.POIFSFileSystem;
import org.docx4j.openpackaging.exceptions.InvalidFormatException;
import org.docx4j.openpackaging.parts.PartName;
import org.docx4j.openpackaging.parts.relationships.Namespaces;


/**
 * You can use oleObjectBinaryPart.setBinaryData( ByteBuffer.wrap(bytes) );
 * to populate this from a byte[]
 * 
 * @author jharrop
 *
 */
public class OleObjectBinaryPart extends BinaryPart {

	private static Logger log = LoggerFactory.getLogger(OleObjectBinaryPart.class);		
	
	public OleObjectBinaryPart(PartName partName) throws InvalidFormatException {
		super(partName);
		init();				
	}

	
	public OleObjectBinaryPart() throws InvalidFormatException {
		super( new PartName("/word/embeddings/oleObject1.bin") );
		init();				
	}
	
	public void init() {
		// Used if this Part is added to [Content_Types].xml 
		setContentType(new  org.docx4j.openpackaging.contenttype.ContentType( 
				org.docx4j.openpackaging.contenttype.ContentTypes.OFFICEDOCUMENT_OLE_OBJECT));
			// should be this, unless it contains eg a doc stored directly (ie a non-generic OLE object)

		// Used when this Part is added to a rels
		setRelationshipType(Namespaces.OLE_OBJECT);
		
		
	}

	POIFSFileSystem fs;
	public POIFSFileSystem getFs() throws IOException {
		if (fs==null) {
			initPOIFSFileSystem();
		}
		return fs;
	}
	
	public void initPOIFSFileSystem() throws IOException {
		
		if (getBuffer()!=null) {

			//fs = new POIFSFileSystem( org.docx4j.utils.BufferUtil.newInputStream(bb) );
			// the above seems to be calling methods which aren't implemented,
			// so, for now, brute force..

			log.info("initing POIFSFileSystem from existing data");
			ByteArrayInputStream bais = new ByteArrayInputStream(this.getBytes());
			fs = new POIFSFileSystem(bais);
			
		} else {

			log.info("creating new empty POIFSFileSystem");
			fs = new POIFSFileSystem();
			writePOIFSFileSystem();
		}
	}
	
	/**
	 * Write any changes which have been made to POIFSFileSystem,
	 * to the underlying ByteBuffer.  This is necessary if the changes
	 * are to be persisted.
	 * 
	 * @throws IOException
	 */
	public void writePOIFSFileSystem() throws IOException {
		
		ByteArrayOutputStream baos = new ByteArrayOutputStream(); 

		getFs().writeFilesystem(baos);
		
		// Need to put this is bb
		byte[] bytes = baos.toByteArray();
		
		// java.nio.ByteBuffer bb contains the data
		setBinaryData( ByteBuffer.wrap(bytes) );
		
	}
	
	
    
    
    public void viewFile(boolean verbose) throws IOException
    {
    	viewFile(System.out, verbose);
    }

    /**
     * @param os
     * @param verbose
     * @throws IOException
     * @since 3.0.0
     */
    public void viewFile(OutputStream os, boolean verbose) throws IOException
    {
    	String indent="";
    	boolean withSizes = true;    	
    	displayDirectory(getFs().getRoot(), os, indent, withSizes);
    	
    	if (verbose) {
	        List strings = POIFSViewEngine.inspectViewable(fs, true, 0, "  ");
			Iterator iter = strings.iterator();
	
			while (iter.hasNext()) {
				os.write( ((String)iter.next()).getBytes());
			}
    	}
    }
    
    /**
     * Adapted from org.apache.poi.poifs.dev.POIFSLister
     * @param dir
     * @param indent
     * @param withSizes
     * @throws IOException 
     * 
     */
    private void displayDirectory(DirectoryNode dir, OutputStream os, String indent, boolean withSizes) throws IOException {
        System.out.println(indent + dir.getName() + " -");
        String newIndent = indent + "  ";

        boolean hadChildren = false;
        for(Iterator<Entry> it = dir.getEntries(); it.hasNext();) {
           hadChildren = true;
           Entry entry = it.next();
           if (entry instanceof DirectoryNode) {
              displayDirectory((DirectoryNode) entry, os, newIndent, withSizes);
           } else {
              DocumentNode doc = (DocumentNode) entry;
              String name = doc.getName();
              String size = "";
              if (name.charAt(0) < 10) {
                 String altname = "(0x0" + (int) name.charAt(0) + ")" + name.substring(1);
                 name = name.substring(1) + " <" + altname + ">";
              }
              if (withSizes) {
                 size = " [" + doc.getSize() + " / 0x" + 
                        Integer.toHexString(doc.getSize()) + "]";
              }
              os.write((newIndent + name + size + "\n").getBytes() );
           }
        }
        if (!hadChildren) {
        	os.write((newIndent + "(no children)").getBytes());
        }
     }
	
}
