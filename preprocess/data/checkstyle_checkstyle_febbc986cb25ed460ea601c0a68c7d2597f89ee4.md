Refactoring Types: ['Rename Package']
yle/test/chapter5naming/rule521packagenames/PackageNameTest.java
package com.google.checkstyle.test.chapter5naming.rule521packagenames;

import java.io.File;
import java.io.IOException;

import org.junit.BeforeClass;
import org.junit.Test;

import com.google.checkstyle.test.base.ConfigurationBuilder;
import com.puppycrawl.tools.checkstyle.api.CheckstyleException;
import com.puppycrawl.tools.checkstyle.api.Configuration; 
import com.puppycrawl.tools.checkstyle.checks.naming.PackageNameCheck;
import com.google.checkstyle.test.base.BaseCheckTestSupport;

public class PackageNameTest extends BaseCheckTestSupport{
    
	private Class<PackageNameCheck> clazz = PackageNameCheck.class;
	private static ConfigurationBuilder builder;
	private static Configuration checkConfig;
	private String msgKey = "name.invalidPattern";
	private static String format;
    
    
    @BeforeClass
    public static void setConfigurationBuilder() throws CheckstyleException, IOException {
        builder = new ConfigurationBuilder(new File("src/it/"));
        checkConfig = builder.getCheckConfig("PackageName");
        format = checkConfig.getAttribute("format");
    }

    @Test
    public void goodPackageNameTest() throws IOException, Exception {
        
        
        final String[] expected = {};
        
        String filePath = builder.getFilePath("PackageNameInputGood");
        
        Integer[] warnList = builder.getLinesWithWarn(filePath);
        verify(checkConfig, filePath, expected, warnList);
    }
    
    @Test
    public void badPackageNameTest() throws IOException, Exception {
        
        String packagePath = "com.google.checkstyle.test.chapter5naming.rule521packageNames";
        String msg = getCheckMessage(checkConfig.getMessages(), msgKey, packagePath, format);

        final String[] expected = {
            "1:9: " + msg,
        };
        
        String filePath = builder.getFilePath("PackageNameInputBad");
        
        Integer[] warnList = builder.getLinesWithWarn(filePath);
        verify(checkConfig, filePath, expected, warnList);
    }

    @Test
    public void badPackageName2Test() throws IOException, Exception {
        
        
        String packagePath = "com.google.checkstyle.test.chapter5naming.rule521_packagenames";
        String msg = getCheckMessage(checkConfig.getMessages(), msgKey, packagePath, format);

        final String[] expected = {
            "1:9: " + msg,
        };
        
        String filePath = builder.getFilePath("BadPackageNameInput2");
        
        Integer[] warnList = builder.getLinesWithWarn(filePath);
        verify(checkConfig, filePath, expected, warnList);
    }
    
    @Test
    public void badPackageName3Test() throws IOException, Exception {
        
        
        String packagePath = "com.google.checkstyle.test.chapter5naming.rule521$packagenames";
        String msg = getCheckMessage(checkConfig.getMessages(), msgKey, packagePath, format);

        final String[] expected = {
            "1:9: " + msg,
        };
        
        String filePath = builder.getFilePath("PackageBadNameInput3");
        
        Integer[] warnList = builder.getLinesWithWarn(filePath);
        verify(checkConfig, filePath, expected, warnList);
    }
}




File: src/it/resources/com/google/checkstyle/test/chapter4formatting/rule4822variabledistance/InputVariableDeclarationUsageDistanceCheck.java
package com.google.checkstyle.test.chapter4formatting.rule4822variabledistance;
import java.util.*;
public class InputVariableDeclarationUsageDistanceCheck {

	private static int test1 = 0;

	static {
		int b = 0;
		int d = 0;
		{
			d = ++b;
		}
	}

	static {
		int c = 0;
		int a = 3;
		int b = 2;
		{
			a = a + b;
			c = b;
		}
		{
			c--;
		}
		a = 7;
	}

	static {
		int a = -1;
		int b = 2;
		b++;
		int c = --b;
		a = b; // DECLARATION OF VARIABLE 'a' SHOULD BE HERE (distance = 2)
	}

	public InputVariableDeclarationUsageDistanceCheck(int test1) {
		int temp = -1;
		this.test1 = test1;
		temp = test1; // DECLARATION OF VARIABLE 'temp' SHOULD BE HERE (distance = 2)
	}

	public boolean testMethod() {
		int temp = 7;
		new InputVariableDeclarationUsageDistanceCheck(2);
		String.valueOf(temp); // DECLARATION OF VARIABLE 'temp' SHOULD BE HERE (distance = 2)
		boolean result = false;
		String str = "";
		if (test1 > 1) {
			str = "123";
			result = true;
		}
		return result;
	}

	public void testMethod2() {
		int count;
		int a = 3;
		int b = 2;
		{
			a = a
					+ b
					- 5
					+ 2
					* a;
			count = b; // DECLARATION OF VARIABLE 'count' SHOULD BE HERE (distance = 2)
		}
	}

	public void testMethod3() {
		int count; //warn
		int a = 3;
		int b = 3;
		a = a + b;
		b = a + a;
		testMethod2();
		count = b; // DECLARATION OF VARIABLE 'count' SHOULD BE HERE (distance = 4)
	}

	public void testMethod4(int arg) {
		int d = 0;
		for (int i = 0; i < 10; i++) {
			d++;
			if (i > 5) {
				d += arg;
			}
		}

		String ar[] = { "1", "2" };
		for (String st : ar) {
			System.out.println(st);
		}
	}

	public void testMethod5() {
		int arg = 7;
		boolean b = true;
		boolean bb = false;
		if (b)
			if (!bb)
				b = false;
		testMethod4(arg); // DECLARATION OF VARIABLE 'arg' SHOULD BE HERE (distance = 2)
	}

	public void testMethod6() {
		int blockNumWithSimilarVar = 3;
		int dist = 0;
		int index = 0;
		int block = 0;

		if (blockNumWithSimilarVar <= 1) {
			do {
				dist++;
				if (block > 4) {
					break;
				}
				index++;
				block++;
			} while (index < 7);
		} else {
			while (index < 8) {
				dist += block;
				index++;
				block++;
			}
		}
	}

	public boolean testMethod7(int a) {
		boolean res;
		switch (a) {
		case 1:
			res = true;
			break;
		default:
			res = false;
		}
		return res;
	}

	public void testMethod8() {
		int b = 0;
		int c = 0;
		int m = 0;
		int n = 0;
		{
			c++;
			b++;
		}
		{
			n++; // DECLARATION OF VARIABLE 'n' SHOULD BE HERE (distance = 2)
			m++; // DECLARATION OF VARIABLE 'm' SHOULD BE HERE (distance = 3)
			b++;
		}
	}

	public void testMethod9() {
		boolean result = false;
		boolean b1 = true;
		boolean b2 = false;
		if (b1) {
			if (!b2) {
				result = true;
			}
			result = true;
		}
	}

	public boolean testMethod10() {
		boolean result;
		try {
			result = true;
		} catch (Exception e) {
			result = false;
		} finally {
			result = false;
		}
		return result;
	}

	public void testMethod11() {
		int a = 0;
		int b = 10;
		boolean result;
		try {
			b--;
		} catch (Exception e) {
			b++;
			result = false; // DECLARATION OF VARIABLE 'result' SHOULD BE HERE (distance = 2)
		} finally {
			a++;
		}
	}

	public void testMethod12() {
		boolean result = false;
		boolean b3 = true;
		boolean b1 = true;
		boolean b2 = false;
		if (b1) {
			if (b3) {
				if (!b2) {
					result = true;
				}
				result = true;
			}
		}
	}

	public void testMethod13() {
		int i = 9;
		int j = 6;
		int g = i + 8;
		int k = j + 10;
	}

	public void testMethod14() {
		Session s = openSession();
		Transaction t = s.beginTransaction(); //warn
		A a = new A();
		E d1 = new E();
		C1 c = new C1();
		E d2 = new E();
		a.setForward(d1);
		d1.setReverse(a);
		c.setForward(d2); // DECLARATION OF VARIABLE 'c' SHOULD BE HERE (distance = 3)
							// DECLARATION OF VARIABLE 'd2' SHOULD BE HERE (distance = 3)
		d2.setReverse(c);
		Serializable aid = s.save(a);
		Serializable d2id = s.save(d2);
		t.commit(); // DECLARATION OF VARIABLE 't' SHOULD BE HERE (distance = 5)
		s.close();
	}

	public boolean isCheckBoxEnabled(int path) {
		String model = "";
		if (true) {
			for (int index = 0; index < path; ++index) {
				int nodeIndex = model.codePointAt(path);
				if (model.contains("")) {
					return false;
				}
			}
		} else {
			int nodeIndex = model.codePointAt(path);
			if (model.contains("")) {
				return false;
			}
		}
		return true;
	}

	public Object readObject(String in) throws Exception {
		String startDay = new String("");
		String endDay = new String("");
		return new String(startDay + endDay);
	}

	public int[] getSelectedIndices() {
		int[] selected = new int[5];
		String model = "";
		int a = 0;
		a++;
		for (int index = 0; index < 5; ++index) {
			selected[index] = Integer.parseInt(model.valueOf(a)); // DECLARATION OF VARIABLE 'selected' SHOULD BE HERE (distance = 2)
																						// DECLARATION OF VARIABLE 'model' SHOULD BE HERE (distance = 2)
		}
		return selected;
	}

	public void testMethod15() {
		String confDebug = "";
		if (!confDebug.equals("") && !confDebug.equals("null")) {
			LogLog.warn("The \"" + "\" attribute is deprecated.");
			LogLog.warn("Use the \"" + "\" attribute instead.");
			LogLog.setInternalDebugging(confDebug, true);
		}

		int i = 0;
		int k = 7;
		boolean b = false;
		for (; i < k; i++) {
			b = true;
			k++;
		}

		int sw;
		switch (i) {
		case 0:
			k++;
			sw = 0; // DECLARATION OF VARIABLE 'sw' SHOULD BE HERE (distance = 2)
			break;
		case 1:
			b = false;
			break;
		default:
			b = true;
		}

		int wh = 0;
		b = true;
		do {
			k--;
			i++;
		} while (wh > 0); // DECLARATION OF VARIABLE 'wh' SHOULD BE HERE (distance = 2)

		if (wh > 0) {
			k++;
		} else if (!b) {
			i++;
		} else {
			i--;
		}
	}

	public void testMethod16() {
		int wh = 1, i = 4, k = 0;
		if (i > 0) {
			k++;
		} else if (wh > 0) {
			i++;
		} else {
			i--;
		}
	}
	
	protected JMenuItem createSubMenuItem(LogLevel level) {
	    final JMenuItem result = new JMenuItem(level.toString());
	    final LogLevel logLevel = level;
	    result.setMnemonic(level.toString().charAt(0));
	    result.addActionListener(new ActionListener() {
	      public void actionPerformed(ActionEvent e) {
	        showLogLevelColorChangeDialog(result, logLevel); // DECLARATION OF VARIABLE 'logLevel' SHOULD BE HERE (distance = 2)
	      }
	    });

	    return result;

	  }
	
	public static Color darker(Color color, double fraction) {
        int red = (int) Math.round(color.getRed() * (1.0 - fraction));
        int green = (int) Math.round(color.getGreen() * (1.0 - fraction));
        int blue = (int) Math.round(color.getBlue() * (1.0 - fraction));

        if (red < 0) {
            red = 0;
        } else if (red > 255) {
            red = 255;
        }
        if (green < 0) { // DECLARATION OF VARIABLE 'green' SHOULD BE HERE (distance = 2)
            green = 0;
        } else if (green > 255) {
            green = 255;
        }
        if (blue < 0) { // DECLARATION OF VARIABLE 'blue' SHOULD BE HERE (distance = 3)
            // blue = 0;
        }

        int alpha = color.getAlpha();

        return new Color(red, green, blue, alpha);
    }
	
	public void testFinal() {
		AuthUpdateTask authUpdateTask = null;
		final long intervalMs = 30 * 60000L;
		Object authCheckUrl = null, authInfo = null;
        authUpdateTask = new AuthUpdateTask(authCheckUrl, authInfo, new IAuthListener() {
            @Override
            public void authTokenChanged(String cookie, String token) {
                fireAuthTokenChanged(cookie, token);
            }
        });

        Timer authUpdateTimer = new Timer("Auth Guard", true);
        authUpdateTimer.schedule(authUpdateTask, intervalMs / 2, intervalMs); // DECLARATION OF VARIABLE 'intervalMs' SHOULD BE HERE (distance = 2)
	}
	
	public void testForCycle() {
		int filterCount = 0;
		for (int i = 0; i < 10; i++, filterCount++) {
			int abc = 0;
			System.out.println(abc);

			for (int j = 0; j < 10; j++) {
				abc = filterCount;
				System.out.println(abc);
			}
		}
	}
	
	public void testIssue32_1()
    {
        Option srcDdlFile = OptionBuilder.create("f");
        Option logDdlFile = OptionBuilder.create("o");
        Option help = OptionBuilder.create("h");

        Options options = new Options();
        options.something();
        options.something();
        options.something();
        options.something();
        options.addOption(srcDdlFile, logDdlFile, help); // distance=1
    }

    public void testIssue32_2()
    {
        int mm = Integer.parseInt("2");
        long timeNow = 0;
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(timeNow);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        cal.set(Calendar.HOUR_OF_DAY, mm);
        cal.set(Calendar.MINUTE, mm); // distance=1
    }
    
    public void testIssue32_3(MyObject[] objects) {
        Calendar cal = Calendar.getInstance();
        for(int i=0; i<objects.length; i++) {
            objects[i].setEnabled(true);
            objects[i].setColor(0x121212);
            objects[i].setUrl("http://google.com");
            objects[i].setSize(789);
            objects[i].setCalendar(cal); // distance=1
        }
    }
    
    public String testIssue32_4(boolean flag) {
        StringBuilder builder = new StringBuilder();
        builder.append("flag is ");
        builder.append(flag);
        final String line = "";
        if(flag) {
            builder.append("line of AST is:");
            builder.append("\n");
            builder.append(String.valueOf(line)); //distance=1
            builder.append("\n");
        }
        return builder.toString();
    }
    
    public void testIssue32_5() {
        Option a = null;
        Option b = null;
        Option c = null;
        boolean isCNull = isNull(c); // distance=1
        boolean isBNull = isNull(b); // distance=1
        boolean isANull = isNull(a); // distance=1
    }
  
    public void testIssue32_6() {
        Option aOpt = null;
        Option bOpt = null;
        Option cOpt = null;
        isNull(cOpt); // distance = 1
        isNull(bOpt); // distance = 2
        isNull(aOpt); // distance = 3
    }
    
    public void testIssue32_7() {
        String line = "abc";
        writer.write(line);
        line.charAt(1);
        builder.append(line);
        test(line, line, line);
    }
    
    public void testIssue32_8(Writer w1, Writer w2, Writer w3) {
        String l1="1";

        
        w3.write(l1); //distance=3
    }
    
    public void testIssue32_9() {
        Options options = new Options();
        Option myOption = null; //warn
        options.addBindFile(null);
        options.addBindFile(null);
        options.addBindFile(null);
        options.addBindFile(null);
        options.addBindFile(null);
        System.out.println("message");
        myOption.setArgName("abc"); // distance=7
    }
    
    public void testIssue32_10() {
        Options options = new Options();
        Option myOption = null; //warn
        options.addBindFile(null);
        options.addBindFile(null);
        options.addBindFile(null);
        options.addBindFile(null);
        options.addBindFile(null);
        myOption.setArgName("q"); // distance=6
    }
    
    
    public int testIssue32_11(String toDir)
            throws Exception
    {
        int count = 0;
        String[] files = {};

        System.out.println("Data archivation started");
        files.notify();
        System.out.println("sss");

        if (files == null || files.length == 0) {
            System.out.println("No files on a remote site");
        }
        else {
            System.out.println("Files on remote site: " + files.length);

            for (String ftpFile : files) {
                if (files.length == 0) {
                    "".concat("");
                    ftpFile.concat(files[2]);
                    count++;
                }
            }
        }

        System.out.println();

        return count;
    }
    
    private Session openSession() {
        return null;
        
    }
    
    class Session {

        public Transaction beginTransaction() {
            return null;
        }

        public void close() {
        }

        public Serializable save(E d2) {
            return null;
        }

        public Serializable save(A a) {
            return null;
        }
        
    }
    
    class Transaction {

        public void commit() {
            
        }
        
    }
    
    class A {

        public void setForward(E d1) {
            
        }
        
    }
    
    class E {

        public void setReverse(C1 c) {
            
        }

        public void setReverse(A a) {
            
        }
        
    }
    
    class C1 {

        public void setForward(E d2) {
            
        }
        
    }
    
    class Serializable {
        
    }
    
    class JMenuItem {

        public JMenuItem(String string) {
        }

        public void addActionListener(ActionListener actionListener) {
            
        }

        public void setMnemonic(char charAt) {
            
        }
        
    }
    
    class LogLevel {
        
    }
    
    class ActionListener {
        
    }
    
    class ActionEvent {
        
    }
    
    private void showLogLevelColorChangeDialog(JMenuItem j, LogLevel l) {   }
    
    static class Color {

        public Color(int red, int green, int blue, int alpha) {
        }

        public double getRed() {
            return 0;
        }

        public int getAlpha() {
            return 0;
        }

        public double getBlue() {
            return 0;
        }

        public double getGreen() {
            return 0;
        }
        
    }
    
    class AuthUpdateTask {

        public AuthUpdateTask(Object authCheckUrl, Object authInfo,
                IAuthListener iAuthListener) {
        }
        
    }
    
    interface IAuthListener {

        void authTokenChanged(String cookie, String token);
        
    }
    
    void fireAuthTokenChanged(String s, String s1) {}
    
    class Timer {

        public Timer(String string, boolean b) {
        }

        public void schedule(AuthUpdateTask authUpdateTask, long l,
                long intervalMs) {
        }
        
    }
    
    class Option {

        public void setArgName(String string) {
        }
        
    }
    
    boolean isNull(Option o) {
		return false;}
    
    class Writer {

        public void write(String l3) {
            
        }
        
    }
    
    class Options {

        public void addBindFile(Object object) {
            
        }

		public void
				addOption(Option srcDdlFile, Option logDdlFile, Option help)
		{
			
		}

		public void something()
		{
			
		}
        
    }
    
    class TreeMapNode {

        public TreeMapNode(String label, double d, DefaultValue defaultValue) {
        }

        public TreeMapNode(String label) {
        }
        
    }

    class DefaultValue {

        public DefaultValue(double d) {
        }
        
    }
    
    static class LogLog {

		public static void warn(String string)
		{
			
		}

		public static void setInternalDebugging(String confDebug, boolean b)
		{
			
		}
    	
    }
    
    static class OptionBuilder {

		public static Option create(String string)
		{
			return null;
		}
    	
    }
    
    class MyObject {

		public void setEnabled(boolean b)
		{
			
		}

		public void setCalendar(Calendar cal)
		{
			
		}

		public void setSize(int i)
		{
			
		}

		public void setUrl(String string)
		{
			
		}

		public void setColor(int i)
		{
			
		}
    	
    }
    
    static class writer {

		public static void write(String line)
		{
			
		}
    	
    }
    
    void test(String s, String s1, String s2) {
    	
    }
    
    static class builder {

		public static void append(String line)
		{
			
		}
    	
    }
    
}