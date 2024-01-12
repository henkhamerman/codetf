Refactoring Types: ['Move Attribute']
uk/src/main/java/org/languagetool/rules/uk/MixedAlphabetsRule.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2005 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.rules.uk;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.ResourceBundle;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.languagetool.AnalyzedSentence;
import org.languagetool.AnalyzedTokenReadings;
import org.languagetool.rules.Category;
import org.languagetool.rules.Rule;
import org.languagetool.rules.RuleMatch;

/**
 * A rule that matches words Latin and Cyrillic characters in them
 * 
 * @author Andriy Rysin
 */
public class MixedAlphabetsRule extends Rule {

  private static final Pattern LIKELY_LATIN_NUMBER = Pattern.compile("[XVIХІ]{2,8}");
  private static final Pattern LATIN_NUMBER_WITH_CYRILLICS = Pattern.compile("Х{1,3}І{1,3}|І{1,3}Х{1,3}|Х{2,3}|І{2,3}");
  private static final Pattern MIXED_ALPHABETS = Pattern.compile(".*([a-zA-Z]'?[а-яіїєґА-ЯІЇЄҐ]|[а-яіїєґА-ЯІЇЄҐ]'?[a-zA-Z]).*");
  private static final Pattern CYRILLIC_ONLY = Pattern.compile(".*[бвгґдєжзйїлнпфцчшщьюяБГҐДЄЖЗИЙЇЛПФЦЧШЩЬЮЯ].*");
  private static final Pattern LATIN_ONLY = Pattern.compile(".*[bdfghjlqrsvzDFGLNQRSUVZ].*");

  public MixedAlphabetsRule(final ResourceBundle messages) throws IOException {
    super.setCategory(new Category(messages.getString("category_misc")));
  }

  @Override
  public final String getId() {
    return "UK_MIXED_ALPHABETS";
  }

  @Override
  public String getDescription() {
    return "Змішування кирилиці й латиниці";
  }

  public String getShort() {
    return "Мішанина розкладок";
  }

  public String getSuggestion(String word) {
    String highlighted = word.replaceAll("([a-zA-Z])([а-яіїєґА-ЯІЇЄҐ])", "$1/$2");
    highlighted = highlighted.replaceAll("([а-яіїєґА-ЯІЇЄҐ])([a-zA-Z])", "$1/$2");
    return " містить суміш кирилиці та латиниці: «"+ highlighted +"», виправлення: ";
  }

  /**
   * Indicates if the rule is case-sensitive. 
   * @return true if the rule is case-sensitive, false otherwise.
   */
  public boolean isCaseSensitive() {
    return true;  
  }

  @Override
  public final RuleMatch[] match(final AnalyzedSentence sentence) {
    List<RuleMatch> ruleMatches = new ArrayList<>();
    AnalyzedTokenReadings[] tokens = sentence.getTokensWithoutWhitespace();

    for (AnalyzedTokenReadings tokenReadings: tokens) {
      String tokenString = tokenReadings.getToken();

      if( MIXED_ALPHABETS.matcher(tokenString).matches() ) {
      
        List<String> replacements = new ArrayList<>();

        if(!LATIN_ONLY.matcher(tokenString).matches() && ! LIKELY_LATIN_NUMBER.matcher(tokenString).matches()) {
          replacements.add( toCyrillic(tokenString) );
        }
        if(!CYRILLIC_ONLY.matcher(tokenString).matches() || LIKELY_LATIN_NUMBER.matcher(tokenString).matches()) {
          replacements.add( toLatin(tokenString) );
        }

        if (replacements.size() > 0) {
          RuleMatch potentialRuleMatch = createRuleMatch(tokenReadings, replacements);
          ruleMatches.add(potentialRuleMatch);
        }
      }
      else if(LATIN_NUMBER_WITH_CYRILLICS.matcher(tokenString).matches()) {
        List<String> replacements = new ArrayList<>();
        replacements.add( toLatin(tokenString) );

        RuleMatch potentialRuleMatch = createRuleMatch(tokenReadings, replacements);
        ruleMatches.add(potentialRuleMatch);
      }
    }
    return toRuleMatchArray(ruleMatches);
  }

  private RuleMatch createRuleMatch(AnalyzedTokenReadings readings, List<String> replacements) {
    String tokenString = readings.getToken();
    String msg = tokenString + getSuggestion(tokenString) + StringUtils.join(replacements, ", ");

    RuleMatch potentialRuleMatch = new RuleMatch(this, readings.getStartPos(), readings.getEndPos(), msg, getShort());
    potentialRuleMatch.setSuggestedReplacements(replacements);

    return potentialRuleMatch;
  }

  @Override
  public void reset() {
  }

  private static final Map<Character, Character> toLatMap = new HashMap<>();
  private static final Map<Character, Character> toCyrMap = new HashMap<>();
  private static final String cyrChars = "аеікморстухАВЕІКМНОРСТУХ";
  private static final String latChars = "aeikmopctyxABEIKMHOPCTYX";

  static {
    for (int i = 0; i < cyrChars.length(); i++) {
      toLatMap.put(cyrChars.charAt(i), latChars.charAt(i));
      toCyrMap.put(latChars.charAt(i), cyrChars.charAt(i));
    }
  }

  private static String toCyrillic(String word) {
    for (Map.Entry<Character, Character> entry : toCyrMap.entrySet()) {
      word = word.replace(entry.getKey(), entry.getValue());
    }
    return word;
  }

  private static String toLatin(String word) {
    for (Map.Entry<Character, Character> entry : toLatMap.entrySet()) {
      word = word.replace(entry.getKey(), entry.getValue());
    }
    return word;
  }

}


File: languagetool-language-modules/uk/src/main/java/org/languagetool/rules/uk/MorfologikUkrainianSpellerRule.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2012 Marcin Miłkowski (http://www.languagetool.org)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */

package org.languagetool.rules.uk;

import java.io.IOException;
import java.util.ResourceBundle;
import java.util.regex.Pattern;

import org.languagetool.AnalyzedToken;
import org.languagetool.AnalyzedTokenReadings;
import org.languagetool.JLanguageTool;
import org.languagetool.Language;
import org.languagetool.rules.spelling.morfologik.MorfologikSpellerRule;
import org.languagetool.tagging.uk.IPOSTag;

public final class MorfologikUkrainianSpellerRule extends MorfologikSpellerRule {

  private static final String ABBREVIATION_CHAR = ".";
  private static final String RESOURCE_FILENAME = "/uk/hunspell/uk_UA.dict";
  private static final Pattern UKRAINIAN_LETTERS = Pattern.compile(".*[а-яіїєґА-ЯІЇЄҐ].*");

  public MorfologikUkrainianSpellerRule(ResourceBundle messages,
                                        Language language) throws IOException {
    super(messages, language);
//    setCheckCompound(true);
  }

  @Override
  public String getFileName() {
    return RESOURCE_FILENAME;
  }

  @Override
  public String getId() {
    return "MORFOLOGIK_RULE_UK_UA";
  }

  @Override
  protected boolean ignoreToken(AnalyzedTokenReadings[] tokens, int idx) throws IOException {
    String word = tokens[idx].getToken();

    // don't check words that don't have Ukrainian letters
    if( ! UKRAINIAN_LETTERS.matcher(word).matches() )
      return true;

    if( super.ignoreToken(tokens, idx) )
      return true;

    if( idx < tokens.length - 1 && tokens[idx+1].getToken().equals(ABBREVIATION_CHAR) ) {
      if( super.ignoreWord(word + ABBREVIATION_CHAR) ) {
        return true;
      }
      if( word.matches("[А-ЯІЇЄҐ]") ) {  //TODO: only do this for initials when last name is followed
        return true;
      }
    }
    
    if( word.contains("-") ) {
      return hasGoodTag(tokens[idx]);
    }

    return false;
  }

  private boolean hasGoodTag(AnalyzedTokenReadings tokens) {
    for (AnalyzedToken analyzedToken : tokens) {
      String posTag = analyzedToken.getPOSTag();
      if( posTag != null 
            && ! posTag.equals(JLanguageTool.SENTENCE_START_TAGNAME) 
            && ! posTag.equals(JLanguageTool.SENTENCE_END_TAGNAME) 
            && ! posTag.contains(IPOSTag.bad.getText()) )
        return true;
    }
    return false;
  }


}


File: languagetool-language-modules/uk/src/main/java/org/languagetool/rules/uk/TokenAgreementRule.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2013 Andriy Rysin
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.rules.uk;

import java.io.IOException;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.ResourceBundle;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.commons.lang.StringUtils;
import org.jetbrains.annotations.Nullable;
import org.languagetool.AnalyzedSentence;
import org.languagetool.AnalyzedToken;
import org.languagetool.AnalyzedTokenReadings;
import org.languagetool.JLanguageTool;
import org.languagetool.language.Ukrainian;
import org.languagetool.rules.Category;
import org.languagetool.rules.Rule;
import org.languagetool.rules.RuleMatch;
import org.languagetool.synthesis.Synthesizer;
import org.languagetool.tagging.uk.IPOSTag;
import org.languagetool.tagging.uk.PosTagHelper;
import org.languagetool.tagging.uk.UkrainianTagger;

/**
 * A rule that checks if tokens in the sentence agree on inflection etc
 * 
 * @author Andriy Rysin
 */
public class TokenAgreementRule extends Rule {
  private static final String NO_VIDMINOK_SUBSTR = ":nv";
  private static final String REQUIRE_VIDMINOK_SUBSTR = ":rv_";
  private static final String VIDMINOK_SUBSTR = ":v_";
  private static final Pattern REQUIRE_VIDMINOK_REGEX = Pattern.compile(":r(v_[a-z]+)");
  private static final Pattern VIDMINOK_REGEX = Pattern.compile(":(v_[a-z]+)");

  private final Ukrainian ukrainian = new Ukrainian();

  private static final Set<String> STREETS = new HashSet<>(Arrays.asList(
      "Штрассе", "Авеню", "Стріт"
      ));

  public TokenAgreementRule(final ResourceBundle messages) throws IOException {
    super.setCategory(new Category(messages.getString("category_misc")));
  }

  @Override
  public final String getId() {
    return "UK_TOKEN_AGREEMENT";
  }

  @Override
  public String getDescription() {
    return "Узгодження слів у реченні";
  }

  public String getShort() {
    return "Узгодження слів у реченні";
  }
  /**
   * Indicates if the rule is case-sensitive. 
   * @return true if the rule is case-sensitive, false otherwise.
   */
  public boolean isCaseSensitive() {
    return false;
  }

  @Override
  public final RuleMatch[] match(final AnalyzedSentence text) {
    List<RuleMatch> ruleMatches = new ArrayList<>();
    AnalyzedTokenReadings[] tokens = text.getTokensWithoutWhitespace();    
    boolean insideMultiword = false;

    AnalyzedTokenReadings reqTokenReadings = null;
    for (int i = 0; i < tokens.length; i++) {
      AnalyzedTokenReadings tokenReadings = tokens[i];

      String posTag = tokenReadings.getAnalyzedToken(0).getPOSTag();

      //TODO: skip conj напр. «бодай»

      if (posTag == null
          || posTag.contains(IPOSTag.unknown.getText())
          || posTag.equals(JLanguageTool.SENTENCE_START_TAGNAME) ){
        reqTokenReadings = null;
        continue;
      }

      AnalyzedToken multiwordReqToken = getMultiwordToken(tokenReadings);
      if( multiwordReqToken != null ) {
        String mwPosTag = multiwordReqToken.getPOSTag();
        if( mwPosTag.startsWith("</") ) {
          insideMultiword = false;
        }
        else {
          insideMultiword = true;
        }
        
        if (mwPosTag.startsWith("</") && mwPosTag.contains(REQUIRE_VIDMINOK_SUBSTR)) { // напр. "згідно з"
          posTag = multiwordReqToken.getPOSTag();
          reqTokenReadings = tokenReadings;
          continue;
        }
        else {
          if( ! mwPosTag.contains("adv") && ! mwPosTag.contains("insert") ) {
            reqTokenReadings = null;
          }
          continue;
        }
      }
      
      if( insideMultiword ) {
        continue;
      }

      String token = tokenReadings.getAnalyzedToken(0).getToken();
      if( posTag.contains(REQUIRE_VIDMINOK_SUBSTR) && tokenReadings.getReadingsLength() == 1 ) {
        String prep = token;

        if( prep.equals("за") && reverseSearch(tokens, i, "що") ) // TODO: move to disambiguator
          continue;

        if( prep.equalsIgnoreCase("понад") )
          continue;

        if( (prep.equalsIgnoreCase("окрім") || prep.equalsIgnoreCase("крім"))
            && tokens.length > i+1 && tokens[i+1].getAnalyzedToken(0).getToken().equalsIgnoreCase("як") ) {
          reqTokenReadings = null;
          continue;
        }

        reqTokenReadings = tokenReadings;
        continue;
      }

      if( reqTokenReadings == null )
        continue;


      // Do actual check

      ArrayList<String> posTagsToFind = new ArrayList<>();
      String reqPosTag = reqTokenReadings.getAnalyzedToken(0).getPOSTag();
      String prep = reqTokenReadings.getAnalyzedToken(0).getLemma();
      
//      AnalyzedToken multiwordToken = getMultiwordToken(tokenReadings);
//      if( multiwordToken != null ) {
//        reqTokenReadings = null;
//        continue;
//      }

      //TODO: for numerics only v_naz
      if( prep.equalsIgnoreCase("понад") ) { //&& tokenReadings.getAnalyzedToken(0).getPOSTag().equals(IPOSTag.numr) ) { 
        posTagsToFind.add("v_naz");
      }
      else if( prep.equalsIgnoreCase("замість") ) {
        posTagsToFind.add("v_naz");
      }

      Matcher matcher = REQUIRE_VIDMINOK_REGEX.matcher(reqPosTag);
      while( matcher.find() ) {
        posTagsToFind.add(matcher.group(1));
      }

      for(AnalyzedToken readingToken: tokenReadings) {
        if( IPOSTag.numr.match(readingToken.getPOSTag()) ) {
          posTagsToFind.add("v_naz");  // TODO: only if noun is following?
          break;
        }
      }

      //      System.out.println("For " + tokenReadings + " to match " + posTagsToFind + " of " + reqTokenReadings.getToken());
      if( ! hasRequiredPosTag(posTagsToFind, tokenReadings) ) {
        if( isTokenToSkip(tokenReadings) )
          continue;

//        if( isTokenToIgnore(tokenReadings) ) {
//          reqTokenReadings = null;
//          continue;
//        }


        //TODO: only for subset: президенти/депутати/мери/гості... or by verb піти/йти/балотуватися/записатися...
        if( prep.equalsIgnoreCase("в") || prep.equalsIgnoreCase("у") || prep.equals("межи") || prep.equals("між") ) {
          if( hasRequiredPosTag(Arrays.asList("p:v_naz"), tokenReadings) ) {
            reqTokenReadings = null;
            continue;
          }
        }

        // на (свято) Купала, на (вулиці) Мазепи, на (вулиці) Тюльпанів
        if (prep.equalsIgnoreCase("на")
            && Character.isUpperCase(token.charAt(0)) && posTag.matches("noun:.:v_rod.*")) {
          reqTokenReadings = null;
          continue;
        }

        if( prep.equalsIgnoreCase("з") ) {
          if( token.equals("рана") ) {
            reqTokenReadings = null;
            continue;
          }
        }
        
        if( prep.equalsIgnoreCase("від") ) {
          if( token.equalsIgnoreCase("а") || token.equals("рана") || token.equals("корки") || token.equals("мала") ) {  // корки/мала ловиться іншим правилом
            reqTokenReadings = null;
            continue;
          }
        }
        else if( prep.equalsIgnoreCase("до") ) {
          if( token.equalsIgnoreCase("я") || token.equals("корки") || token.equals("велика") ) {  // корки/велика ловиться іншим правилом
            reqTokenReadings = null;
            continue;
          }
        }

        // exceptions
        if( tokens.length > i+1 ) {
          //      if( tokens.length > i+1 && Character.isUpperCase(tokenReadings.getAnalyzedToken(0).getToken().charAt(0))
          //        && hasRequiredPosTag(Arrays.asList("v_naz"), tokenReadings)
          //        && Character.isUpperCase(tokens[i+1].getAnalyzedToken(0).getToken().charAt(0)) )
          //          continue; // "у Конан Дойла", "у Робін Гуда"

          if( isCapitalized( token ) 
              && STREETS.contains( tokens[i+1].getAnalyzedToken(0).getToken()) ) {
            reqTokenReadings = null;
            continue;
          }

          if( IPOSTag.isNum(tokens[i+1].getAnalyzedToken(0).getPOSTag())
              && (token.equals("мінус") || token.equals("плюс")
                  || token.equals("мінімум") || token.equals("максимум") ) ) {
            reqTokenReadings = null;
            continue;
          }

          // на мохом стеленому дні - пропускаємо «мохом»
          if( PosTagHelper.hasPosTag(tokenReadings, "noun:.:v_oru.*")
              && tokens[i+1].hasPartialPosTag("adjp") ) {
            continue;
          }
          
          if( (prep.equalsIgnoreCase("через") || prep.equalsIgnoreCase("на"))  // років 10, відсотки 3-4
              && (posTag.startsWith("noun:p:v_naz") || posTag.startsWith("noun:p:v_rod")) // token.equals("років") 
              && IPOSTag.isNum(tokens[i+1].getAnalyzedToken(0).getPOSTag()) ) {
            reqTokenReadings = null;
            continue;
          }

          if( (token.equals("вами") || token.equals("тобою") || token.equals("їми"))
              && tokens[i+1].getAnalyzedToken(0).getToken().startsWith("ж") ) {
            continue;
          }
          if( (token.equals("собі") || token.equals("йому") || token.equals("їм"))
              && tokens[i+1].getAnalyzedToken(0).getToken().startsWith("подібн") ) {
            continue;
          }
          if( (token.equals("усім") || token.equals("всім"))
              && tokens[i+1].getAnalyzedToken(0).getToken().startsWith("відом") ) {
            continue;
          }

          if( prep.equalsIgnoreCase("до") && token.equals("схід") 
                && tokens[i+1].getAnalyzedToken(0).getToken().equals("сонця") ) {
            reqTokenReadings = null;
            continue;
          }
          
          if( tokens[i+1].getAnalyzedToken(0).getToken().equals("«") 
              && tokens[i].getAnalyzedToken(0).getPOSTag().contains(":abbr") ) {
            reqTokenReadings = null;
            continue;
          }

          if( tokens.length > i+2 ) {
            // спиралося на місячної давнини рішення
            if (/*prep.equalsIgnoreCase("на") &&*/ posTag.matches("adj.*:[mfn]:v_rod.*")) {
              String gender = PosTagHelper.getGender(posTag);
              if ( PosTagHelper.hasPosTag(tokens[i+1], "noun.*:"+gender+":v_rod.*")) {
                i += 1;
                continue;
              }
            }

            if ((token.equals("нікому") || token.equals("ніким") || token.equals("нічим") || token.equals("нічому")) 
                && tokens[i+1].getAnalyzedToken(0).getToken().equals("не")) {
              //          reqTokenReadings = null;
              continue;
            }
//            // спиралося на місячної давнини рішення
//            if (prep.equalsIgnoreCase("на") && posTag.matches("adj.*:[mfn]:v_rod.*")) {
//              String gender = PosTagHelper.getGender(posTag);
//              if ( hasPosTag(tokens[i+1], "noun.*:"+gender+":v_rod.*")) {
//                i+=1;
//                continue;
//              }
//            }
          }
        }

        RuleMatch potentialRuleMatch = createRuleMatch(tokenReadings, reqTokenReadings, posTagsToFind);
        ruleMatches.add(potentialRuleMatch);
      }

      reqTokenReadings = null;
    }

    return toRuleMatchArray(ruleMatches);
  }

  private static boolean isCapitalized(String token) {
    return token.length() > 1 && Character.isUpperCase(token.charAt(0)) && Character.isLowerCase(token.charAt(1));
  }

  private boolean reverseSearch(AnalyzedTokenReadings[] tokens, int pos, String string) {
    for(int i=pos-1; i >= 0 && i > pos-4; i--) {
      if( tokens[i].getAnalyzedToken(0).getToken().equalsIgnoreCase(string) )
        return true;
    }
    return false;
  }

  private boolean forwardSearch(AnalyzedTokenReadings[] tokens, int pos, String string, int maxSkip) {
    for(int i=pos+1; i < tokens.length && i <= pos + maxSkip; i++) {
      if( tokens[i].getAnalyzedToken(0).getToken().equalsIgnoreCase(string) )
        return true;
    }
    return false;
  }

  private boolean isTokenToSkip(AnalyzedTokenReadings tokenReadings) {
    for(AnalyzedToken token: tokenReadings) {
//      System.out.println("    tag: " + token.getPOSTag() + " for " + token.getToken());
      if( IPOSTag.adv.match(token.getPOSTag())
          || IPOSTag.contains(token.getPOSTag(), "adv>")
          ||  IPOSTag.insert.match(token.getPOSTag()) )
        return true;
    }
    return false;
  }

//  private boolean isTokenToIgnore(AnalyzedTokenReadings tokenReadings) {
//    for(AnalyzedToken token: tokenReadings) {
//      if( token.getPOSTag().contains("abbr") )
//        return true;
//    }
//    return false;
//  }

  private boolean hasRequiredPosTag(Collection<String> posTagsToFind, AnalyzedTokenReadings tokenReadings) {
    boolean vidminokFound = false;  // because POS dictionary is not complete

    for(AnalyzedToken token: tokenReadings) {
      String posTag = token.getPOSTag();

      if( posTag == null ) {
        if( tokenReadings.getReadingsLength() == 1) 
          return true;
        
        continue;
      }
      
      if( posTag.contains(NO_VIDMINOK_SUBSTR) )
        return true;

      if( posTag.contains(VIDMINOK_SUBSTR) ) {
        vidminokFound = true;

        for(String posTagToFind: posTagsToFind) {
          //          System.out.println("  verifying: " + token + " -> " + posTag + " ~ " + posTagToFind);

          if ( posTag.contains(posTagToFind) )
            return true;
        }
      }
    }

    return ! vidminokFound; //false;
  }

  private RuleMatch createRuleMatch(AnalyzedTokenReadings tokenReadings, AnalyzedTokenReadings reqTokenReadings, List<String> posTagsToFind) {
    String tokenString = tokenReadings.getToken();

    Synthesizer ukrainianSynthesizer = ukrainian.getSynthesizer();

    ArrayList<String> suggestions = new ArrayList<>();
    String oldPosTag = tokenReadings.getAnalyzedToken(0).getPOSTag();
    String requiredPostTagsRegEx = ":(" + StringUtils.join(posTagsToFind,"|") + ")";
    String posTag = oldPosTag.replaceFirst(":v_[a-z]+", requiredPostTagsRegEx);

    //    System.out.println("  creating suggestion for " + tokenReadings + " / " + tokenReadings.getAnalyzedToken(0) +" and tag " + posTag);

    try {
      String[] synthesized = ukrainianSynthesizer.synthesize(tokenReadings.getAnalyzedToken(0), posTag, true);

      //      System.out.println("Synthesized: " + Arrays.asList(synthesized));
      suggestions.addAll( Arrays.asList(synthesized) );
    } catch (IOException e) {
      throw new RuntimeException(e);
    }

    ArrayList<String> reqVidminkyNames = new ArrayList<>();
    for (String vidm: posTagsToFind) {
      reqVidminkyNames.add(UkrainianTagger.VIDMINKY_MAP.get(vidm));
    }

    ArrayList<String> foundVidminkyNames = new ArrayList<>();
    for(AnalyzedToken token: tokenReadings) {
      String posTag2 = token.getPOSTag();
      if( posTag2 != null && posTag2.contains(VIDMINOK_SUBSTR) ) {
        String vidmName = UkrainianTagger.VIDMINKY_MAP.get(posTag2.replaceFirst("^.*"+VIDMINOK_REGEX+".*$", "$1"));
        if( foundVidminkyNames.contains(vidmName) ) {
          if (posTag2.contains(":p:")) {
            vidmName = vidmName + " (мн.)";
            foundVidminkyNames.add(vidmName);
          }
          // else skip dup
        }
        else {
          foundVidminkyNames.add(vidmName);
        }
      }
    }

    String msg = MessageFormat.format("Прийменник «{0}» вимагає іншого відмінка: {1}, а знайдено: {2}", 
        reqTokenReadings.getToken(), StringUtils.join(reqVidminkyNames, ", "), StringUtils.join(foundVidminkyNames, ", "));
        
    if( tokenString.equals("їх") ) {
      msg += ". Можливо тут потрібно присвійний займенник «їхній»?";
      try {
        String newYihPostag = "adj:p" + requiredPostTagsRegEx + ".*";
        String[] synthesized = ukrainianSynthesizer.synthesize(new AnalyzedToken("їхній", "adj:m:v_naz:&pron", "їхній"), newYihPostag, true);
        suggestions.addAll( Arrays.asList(synthesized) );
      } catch (IOException e) {
        throw new RuntimeException(e);
      }
    }
    else if( reqTokenReadings.getToken().equalsIgnoreCase("о") ) {
      for(AnalyzedToken token: tokenReadings.getReadings()) {
        String posTag2 = token.getPOSTag();
        if( posTag2.matches(".*:v_naz.*:anim.*") ) {
          msg += ". Можливо тут «о» — це вигук і потрібно кличний відмінок?";
          try {
            String newPostag = posTag2.replace("v_naz", "v_kly");
            String[] synthesized = ukrainianSynthesizer.synthesize(token, newPostag, false);
            for (String string : synthesized) {
              if( ! string.equals(token.getToken()) && ! suggestions.contains(string) ) {
                suggestions.add( string );
              }
            }
            break;
          } catch (IOException e) {
            throw new RuntimeException(e);
          }
        }
      }
      
    }
        
    RuleMatch potentialRuleMatch = new RuleMatch(this, tokenReadings.getStartPos(), tokenReadings.getEndPos(), msg, getShort());

    potentialRuleMatch.setSuggestedReplacements(suggestions);

    return potentialRuleMatch;
  }

  @Nullable
  private static AnalyzedToken getMultiwordToken(AnalyzedTokenReadings analyzedTokenReadings) {
      for(AnalyzedToken analyzedToken: analyzedTokenReadings) {
        String posTag = analyzedToken.getPOSTag();
        if( posTag != null && posTag.startsWith("<") )
          return analyzedToken;
      }
      return null;
  }

  @Override
  public void reset() {
  }

}


File: languagetool-language-modules/uk/src/main/java/org/languagetool/rules/uk/UkrainianWordRepeatRule.java
package org.languagetool.rules.uk;

import java.util.*;

import org.languagetool.AnalyzedToken;
import org.languagetool.AnalyzedTokenReadings;
import org.languagetool.JLanguageTool;
import org.languagetool.Language;
import org.languagetool.rules.RuleMatch;
import org.languagetool.rules.WordRepeatRule;
import org.languagetool.tagging.uk.IPOSTag;
import org.languagetool.tagging.uk.PosTagHelper;

/**
 * @since 2.9
 */
public class UkrainianWordRepeatRule extends WordRepeatRule {
  private static final HashSet<String> REPEAT_ALLOWED_SET = new HashSet<>(
      Arrays.asList("що", "ні", "одне", "ось")
  );
  private static final HashSet<String> REPEAT_ALLOWED_CAPS_SET = new HashSet<>(
      Arrays.asList("ПРО", "Джей", "Ді")
  );

  public UkrainianWordRepeatRule(ResourceBundle messages, Language language) {
    super(messages, language);
  }

  @Override
  public String getId() {
    return "UKRAINIAN_WORD_REPEAT_RULE";
  }

  @Override
  public boolean ignore(AnalyzedTokenReadings[] tokens, int position) {
    AnalyzedTokenReadings analyzedTokenReadings = tokens[position];
    String token = analyzedTokenReadings.getToken();
    
    // від добра добра не шукають
    if( position > 1 && token.equals("добра")
        && tokens[position-2].getToken().equalsIgnoreCase("від") )
      return true;
    
    if( REPEAT_ALLOWED_SET.contains(token.toLowerCase()) )
      return true;

    if( REPEAT_ALLOWED_CAPS_SET.contains(token) )
      return true;
    
    if( PosTagHelper.hasPosTag(analyzedTokenReadings, "date|time|number") )
      return true;
    
    for(AnalyzedToken analyzedToken: analyzedTokenReadings.getReadings()) {
      String posTag = analyzedToken.getPOSTag();
      if( posTag != null ) {
        if ( ! isInitial(analyzedToken, tokens, position)
//            && ! posTag.equals(JLanguageTool.SENTENCE_START_TAGNAME)
            && ! posTag.equals(JLanguageTool.SENTENCE_END_TAGNAME) )
          return false;
      }
    }
    return true;
  }

  private boolean isInitial(AnalyzedToken analyzedToken, AnalyzedTokenReadings[] tokens, int position) {
    return analyzedToken.getPOSTag().contains(IPOSTag.abbr.getText())
        || (analyzedToken.getToken().length() == 1 
        && Character.isUpperCase(analyzedToken.getToken().charAt(0))
        && position < tokens.length-1 && tokens[position+1].getToken().equals("."));
  }

  @Override
  protected RuleMatch createRuleMatch(String prevToken, String token, int prevPos, int pos, String msg) {
    boolean doubleI = prevToken.equals("І") && token.equals("і");
    if( doubleI ) {
      msg += " або, можливо, перша І має бути латинською.";
    }
    
    RuleMatch ruleMatch = super.createRuleMatch(prevToken, token, prevPos, pos, msg);

    if( doubleI ) {
      List<String> replacements = new ArrayList<>(ruleMatch.getSuggestedReplacements());
      replacements.add("I і");
      ruleMatch.setSuggestedReplacements(replacements);
    }
    return ruleMatch;
  }
}


File: languagetool-language-modules/uk/src/main/java/org/languagetool/tagging/uk/PosTagHelper.java
package org.languagetool.tagging.uk;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.jetbrains.annotations.Nullable;
import org.languagetool.AnalyzedToken;
import org.languagetool.AnalyzedTokenReadings;

/**
 * @since 2.9
 */
public class PosTagHelper {
  private static final Pattern GENDER_REGEX = Pattern.compile("(noun|adjp?|numr):(.):v_.*");
  private static final Pattern GENDER_CONJ_REGEX = Pattern.compile("(noun|adjp?|numr):(.:v_...).*");

  private PosTagHelper() {
  }
  
  @Nullable
  public static String getGender(String posTag) {
    Matcher pos4matcher = GENDER_REGEX.matcher(posTag);
    if( pos4matcher.matches() ) {
      return pos4matcher.group(2);
    }

    return null;
  }

  @Nullable
  public static String getNum(String posTag) {
    Matcher pos4matcher = Pattern.compile("(noun|adjp?|numr):(.):v_.*").matcher(posTag);
    if( pos4matcher.matches() ) {
      String group = pos4matcher.group(2);
      if( ! group.equals("p") ) {
        group = "s";
      }
      return group;
    }
  
    return null;
  }

  @Nullable
  public static String getConj(String posTag) {
    Matcher pos4matcher = Pattern.compile("(noun|adjp?|numr):[mfnp]:(v_...).*").matcher(posTag);
    if( pos4matcher.matches() )
      return pos4matcher.group(2);
  
    return null;
  }

  @Nullable
  public static String getGenderConj(String posTag) {
    Matcher pos4matcher = GENDER_CONJ_REGEX.matcher(posTag);
    if( pos4matcher.matches() )
      return pos4matcher.group(2);

    return null;
  }

  public static boolean hasPosTag(AnalyzedTokenReadings analyzedTokenReadings, String posTagRegex) {
    for(AnalyzedToken analyzedToken: analyzedTokenReadings) {
      if( hasPosTag(analyzedToken, posTagRegex) )
        return true;
    }
    return false;
  }

  public static boolean hasPosTag(AnalyzedToken analyzedToken, String posTagRegex) {
    String posTag = analyzedToken.getPOSTag();
    return posTag != null && posTag.matches(posTagRegex);
  }

//private static String getNumAndConj(String posTag) {
//  Matcher pos4matcher = GENDER_CONJ_REGEX.matcher(posTag);
//  if( pos4matcher.matches() ) {
//    String group = pos4matcher.group(2);
//    if( group.charAt(0) != 'p' ) {
//      group = "s" + group.substring(1);
//    }
//    return group;
//  }
//
//  return null;
//}

}


File: languagetool-language-modules/uk/src/main/java/org/languagetool/tagging/uk/UkrainianTagger.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2006 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.tagging.uk;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Scanner;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.jetbrains.annotations.Nullable;
import org.languagetool.AnalyzedToken;
import org.languagetool.JLanguageTool;
import org.languagetool.tagging.BaseTagger;
import org.languagetool.tagging.TaggedWord;
import org.languagetool.tagging.WordTagger;

/** 
 * Ukrainian part-of-speech tagger.
 * See README for details, the POS tagset is described in tagset.txt
 * 
 * @author Andriy Rysin
 */
public class UkrainianTagger extends BaseTagger {

  public static final Map<String, String> VIDMINKY_MAP;

  private static final String NV_TAG = ":nv";
  private static final String COMPB_TAG = ":compb";
//  private static final String V_U_TAG = ":v-u";
  private static final Pattern EXTRA_TAGS = Pattern.compile("(:(v-u|np|ns|bad|slang|rare))+");
//  private static final Pattern EXTRA_TAGS_DOUBLE = Pattern.compile("(:(nv|np|ns))+");
  private static final String DEBUG_COMPOUNDS_PROPERTY = "org.languagetool.tagging.uk.UkrainianTagger.debugCompounds";
  private static final String TAG_ANIM = ":anim";
  
  private static final Pattern MNP_NAZ_REGEX = Pattern.compile(".*:[mnp]:v_naz.*");
  private static final Pattern MNP_ZNA_REGEX = Pattern.compile(".*:[mnp]:v_zna.*");
  private static final Pattern MNP_ROD_REGEX = Pattern.compile(".*:[mnp]:v_rod.*");
  private static final Pattern NOUN_SING_V_ROD_REGEX = Pattern.compile("noun:[mfn]:v_rod.*");
  private static final Pattern NOUN_V_NAZ_REGEX = Pattern.compile("noun:.:v_naz.*");
  private static final Pattern SING_REGEX_F = Pattern.compile(":[mfn]:");
  private static final Pattern O_ADJ_PATTERN = Pattern.compile(".*(о|[чшщ]е)");
  
//  private static final String VERB_TAG_FOR_REV_IMPR = IPOSTag.verb.getText()+":rev:impr";
//  private static final String VERB_TAG_FOR_IMPR = IPOSTag.verb.getText()+":impr";
  private static final String ADJ_TAG_FOR_PO_ADV_MIS = IPOSTag.adj.getText() + ":m:v_mis";
  private static final String ADJ_TAG_FOR_PO_ADV_NAZ = IPOSTag.adj.getText() + ":m:v_naz";
  // full latin number regex: M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})
  private static final Pattern NUMBER = Pattern.compile("[+-±]?[€₴\\$]?[0-9]+(,[0-9]+)?([-–—][0-9]+(,[0-9]+)?)?(%|°С?)?|(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})");
  private static final Pattern DATE = Pattern.compile("[\\d]{2}\\.[\\d]{2}\\.[\\d]{4}");
  private static final Pattern TIME = Pattern.compile("([01]?[0-9]|2[0-3])[.:][0-5][0-9]");
  private static final String stdNounTag = IPOSTag.noun.getText() + ":.:v_";
  private static final int stdNounTagLen = stdNounTag.length();
  private static final Pattern stdNounTagRegex = Pattern.compile(stdNounTag + ".*");
//  private static final Pattern stdNounNvTagRegex = Pattern.compile(IPOSTag.noun.getText() + ".*:nv.*");
  private static final Set<String> dashPrefixes;
  private static final Set<String> leftMasterSet;
  private static final Set<String> cityAvenue = new HashSet<>(Arrays.asList("сіті", "авеню", "стріт", "штрассе"));
  private static final Map<String, Pattern> rightPartsWithLeftTagMap = new HashMap<>();
  private static final Set<String> slaveSet;
  
  private List<String> LEFT_O_ADJ = Arrays.asList(
    "австро", "адиго", "американо", "англо", "афро", "еко", "етно", "індо", "іспано", "києво", 
    "марокано", "угро"
  ); 
  
  private static final Map<String, List<String>> NUMR_ENDING_MAP;
  private BufferedWriter compoundUnknownDebugWriter;
  private BufferedWriter compoundTaggedDebugWriter;
  private BufferedWriter taggedDebugWriter;

  static {
    Map<String, String> map = new LinkedHashMap<>();
    map.put("v_naz", "називний");
    map.put("v_rod", "родовий");
    map.put("v_dav", "давальний");
    map.put("v_zna", "знахідний");
    map.put("v_oru", "орудний");
    map.put("v_mis", "місцевий");
    map.put("v_kly", "кличний");
    VIDMINKY_MAP = Collections.unmodifiableMap(map);

    Map<String, List<String>> map2 = new HashMap<>();
    map2.put("й", Arrays.asList(":m:v_naz", ":m:v_zna"));
    map2.put("го", Arrays.asList(":m:v_rod", ":m:v_zna", ":n:v_rod"));
    map2.put("му", Arrays.asList(":m:v_dav", ":m:v_mis", ":n:v_dav", ":n:v_mis", ":f:v_zna"));  // TODO: depends on the last digit
//    map2.put("им", Arrays.asList(":m:v_oru", ":n:v_oru"));
//    map2.put("ім", Arrays.asList(":m:v_mis", ":n:v_mis"));
//    map2.put("ша", Arrays.asList(":f:v_naz"));
//    map2.put("га", Arrays.asList(":f:v_naz"));
//    map2.put("та", Arrays.asList(":f:v_naz"));
//    map2.put("тої", Arrays.asList(":f:v_rod"));
//    map2.put("тій", Arrays.asList(":f:v_dav", ":f:v_mis"));
//    map2.put("ту", Arrays.asList(":f:v_zna"));
//    map2.put("тою", Arrays.asList(":f:v_oru"));
    map2.put("те", Arrays.asList(":n:v_naz", ":n:v_zna"));
    map2.put("ті", Arrays.asList(":p:v_naz", ":p:v_zna"));
    map2.put("х", Arrays.asList(":p:v_rod", ":p:v_zna"));
    NUMR_ENDING_MAP = Collections.unmodifiableMap(map2);
    
    rightPartsWithLeftTagMap.put("бо", Pattern.compile("(verb(:rev)?:impr|.*pron|noun|adv|excl|part|predic).*"));
    rightPartsWithLeftTagMap.put("но", Pattern.compile("(verb(:rev)?:(impr|futr)|excl).*")); 
    rightPartsWithLeftTagMap.put("от", Pattern.compile("(.*pron|adv|part).*"));
    rightPartsWithLeftTagMap.put("то", Pattern.compile("(.*pron|noun|adv|part|conj).*"));
    rightPartsWithLeftTagMap.put("таки", Pattern.compile("(verb(:rev)?:(futr|past|pres)|.*pron|noun|part|predic|insert).*")); 
    
    dashPrefixes = loadSet("/uk/dash_prefixes.txt");
    leftMasterSet = loadSet("/uk/dash_left_master.txt");
    slaveSet = loadSet("/uk/dash_slaves.txt");
    // TODO: "бабуся", "лялька", "рятівник" - not quite slaves, could be masters too
  }

  private static Set<String> loadSet(String path) {
    Set<String> result = new HashSet<>();
    try (InputStream is = JLanguageTool.getDataBroker().getFromResourceDirAsStream(path);
         Scanner scanner = new Scanner(is,"UTF-8")) {
      while (scanner.hasNextLine()) {
        String line = scanner.nextLine();
        result.add(line);
      }
      return result;
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  @Override
  public String getManualAdditionsFileName() {
    return "/uk/added.txt";
  }

  public UkrainianTagger() {
    super("/uk/ukrainian.dict", new Locale("uk", "UA"), false);
    if( Boolean.valueOf( System.getProperty(DEBUG_COMPOUNDS_PROPERTY) ) ) {
      debugCompounds();
    }
  }

  @Override
  public List<AnalyzedToken> additionalTags(String word, WordTagger wordTagger) {
    if ( NUMBER.matcher(word).matches() ) {
      List<AnalyzedToken> additionalTaggedTokens = new ArrayList<>();
      additionalTaggedTokens.add(new AnalyzedToken(word, IPOSTag.number.getText(), word));
      return additionalTaggedTokens;
    }

    if ( TIME.matcher(word).matches() ) {
      List<AnalyzedToken> additionalTaggedTokens = new ArrayList<>();
      additionalTaggedTokens.add(new AnalyzedToken(word, IPOSTag.time.getText(), word));
      return additionalTaggedTokens;
    }

    if ( DATE.matcher(word).matches() ) {
      List<AnalyzedToken> additionalTaggedTokens = new ArrayList<>();
      additionalTaggedTokens.add(new AnalyzedToken(word, IPOSTag.date.getText(), word));
      return additionalTaggedTokens;
    }
    
    if ( word.contains("-") ) {
      List<AnalyzedToken> guessedCompoundTags = guessCompoundTag(word);
      debug_compound_tagged_write(guessedCompoundTags);
      
      return guessedCompoundTags;
    }
    
    return null;
  }

  @Nullable
  private List<AnalyzedToken> guessCompoundTag(String word) {
    int dashIdx = word.lastIndexOf('-');
    if( dashIdx == 0 || dashIdx == word.length() - 1 )
      return null;

    int firstDashIdx = word.indexOf('-');
    if( dashIdx != firstDashIdx )
      return null;

    String leftWord = word.substring(0, dashIdx);
    String rightWord = word.substring(dashIdx + 1);

    List<TaggedWord> leftWdList = tagBothCases(leftWord);

    if( rightPartsWithLeftTagMap.containsKey(rightWord) ) {
      if( leftWdList.isEmpty() )
        return null;

      Pattern leftTagRegex = rightPartsWithLeftTagMap.get(rightWord);
      
      List<AnalyzedToken> leftAnalyzedTokens = asAnalyzedTokenListForTaggedWords(leftWord, leftWdList);
      List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>(leftAnalyzedTokens.size());
      for (AnalyzedToken analyzedToken : leftAnalyzedTokens) {
        String posTag = analyzedToken.getPOSTag();
        if( posTag != null && leftTagRegex.matcher(posTag).matches() ) {
          newAnalyzedTokens.add(new AnalyzedToken(word, posTag, analyzedToken.getLemma()));
        }
      }
      
      return newAnalyzedTokens.isEmpty() ? null : newAnalyzedTokens;
    }

    if( NUMBER.matcher(leftWord).matches() ) {
      List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>();
      // e.g. 101-го
      if( NUMR_ENDING_MAP.containsKey(rightWord) ) {
        List<String> tags = NUMR_ENDING_MAP.get(rightWord);
        for (String tag: tags) {
          // TODO: shall it be numr or adj?
          newAnalyzedTokens.add(new AnalyzedToken(word, IPOSTag.adj.getText()+tag, leftWord + "-" + "й"));
        }
      }
      else {
        List<TaggedWord> rightWdList = wordTagger.tag(rightWord);
        if( rightWdList.isEmpty() )
          return null;

        List<AnalyzedToken> rightAnalyzedTokens = asAnalyzedTokenListForTaggedWords(rightWord, rightWdList);

        // e.g. 100-річному
        for (AnalyzedToken analyzedToken : rightAnalyzedTokens) {
          if( analyzedToken.getPOSTag().startsWith(IPOSTag.adj.getText()) ) {
            newAnalyzedTokens.add(new AnalyzedToken(word, analyzedToken.getPOSTag(), leftWord + "-" + analyzedToken.getLemma()));
          }
        }
      }
      return newAnalyzedTokens.isEmpty() ? null : newAnalyzedTokens;
    }

    if( leftWord.equalsIgnoreCase("по") && rightWord.endsWith("ськи") ) {
      rightWord += "й";
    }

    List<TaggedWord> rightWdList = wordTagger.tag(rightWord);
    if( rightWdList.isEmpty() )
      return null;

    List<AnalyzedToken> rightAnalyzedTokens = asAnalyzedTokenListForTaggedWords(rightWord, rightWdList);

    if( leftWord.equalsIgnoreCase("по") ) {
      if( rightWord.endsWith("ому") ) {
        return poAdvMatch(word, rightAnalyzedTokens, ADJ_TAG_FOR_PO_ADV_MIS);
      }
      else if( rightWord.endsWith("ський") ) {
        return poAdvMatch(word, rightAnalyzedTokens, ADJ_TAG_FOR_PO_ADV_NAZ);
      }
      return null;
    }

    if( dashPrefixes.contains( leftWord ) || dashPrefixes.contains( leftWord.toLowerCase() ) ) {
      return getNvPrefixNounMatch(word, rightAnalyzedTokens, leftWord);
    }

    if( word.startsWith("пів-") && Character.isUpperCase(word.charAt(4)) ) {
      List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>(rightAnalyzedTokens.size());
      
      for (AnalyzedToken rightAnalyzedToken : rightAnalyzedTokens) {
        String rightPosTag = rightAnalyzedToken.getPOSTag();

        if( rightPosTag == null )
          continue;

        if( NOUN_SING_V_ROD_REGEX.matcher(rightPosTag).matches() ) {
          for(String vid: VIDMINKY_MAP.keySet()) {
            if( vid.equals("v_kly") )
              continue;
            String posTag = rightPosTag.replace("v_rod", vid);
            newAnalyzedTokens.add(new AnalyzedToken(word, posTag, word));
          }
        }
      }

      return newAnalyzedTokens;
    }

    if( Character.isUpperCase(leftWord.charAt(0)) && cityAvenue.contains(rightWord) ) {
      if( leftWdList.isEmpty() )
        return null;
      
      List<AnalyzedToken> leftAnalyzedTokens = asAnalyzedTokenListForTaggedWords(leftWord, leftWdList);
      return cityAvenueMatch(word, leftAnalyzedTokens);
    }

    if( ! leftWdList.isEmpty() ) {
      List<AnalyzedToken> leftAnalyzedTokens = asAnalyzedTokenListForTaggedWords(leftWord, leftWdList);

      List<AnalyzedToken> tagMatch = tagMatch(word, leftAnalyzedTokens, rightAnalyzedTokens);
      if( tagMatch != null ) {
        return tagMatch;
      }
    }

    if( O_ADJ_PATTERN.matcher(leftWord).matches() ) {
      return oAdjMatch(word, rightAnalyzedTokens, leftWord);
    }

    debug_compound_unknown_write(word);
    
    return null;
  }

  private List<TaggedWord> tagBothCases(String leftWord) {
    List<TaggedWord> leftWdList = wordTagger.tag(leftWord);
    String leftLowerCase = leftWord.toLowerCase(conversionLocale);
    if( ! leftWord.equals(leftLowerCase)) {
      leftWdList.addAll(wordTagger.tag(leftLowerCase));
    }
    else {
      String leftUpperCase = capitalize(leftWord);
      if( ! leftWord.equals(leftUpperCase)) {
        leftWdList.addAll(wordTagger.tag(leftUpperCase));
      }
    }

    return leftWdList;
  }

  private String capitalize(String word) {
    return word.substring(0, 1).toUpperCase(conversionLocale) + word.substring(1, word.length());
  }

  private List<AnalyzedToken> cityAvenueMatch(String word, List<AnalyzedToken> leftAnalyzedTokens) {
    List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>(leftAnalyzedTokens.size());
    
    for (AnalyzedToken analyzedToken : leftAnalyzedTokens) {
      String posTag = analyzedToken.getPOSTag();
      if( NOUN_V_NAZ_REGEX.matcher(posTag).matches() ) {
        newAnalyzedTokens.add(new AnalyzedToken(word, posTag.replaceFirst("v_naz", "nv"), word));
      }
    }
    
    return newAnalyzedTokens.isEmpty() ? null : newAnalyzedTokens;
  }
  
  private List<AnalyzedToken> tagMatch(String word, List<AnalyzedToken> leftAnalyzedTokens, List<AnalyzedToken> rightAnalyzedTokens) {
    List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>();
    List<AnalyzedToken> newAnalyzedTokensAnimInanim = new ArrayList<>();
    
    String animInanimNotTagged = null;
    
    for (AnalyzedToken leftAnalyzedToken : leftAnalyzedTokens) {
      String leftPosTag = leftAnalyzedToken.getPOSTag();
      
      if( leftPosTag == null )
        continue;

      String leftPosTagExtra = "";
      boolean leftNv = false;

      if( leftPosTag.contains(NV_TAG) ) {
        leftNv = true;
        leftPosTag = leftPosTag.replace(NV_TAG, "");
      }

      Matcher matcher = EXTRA_TAGS.matcher(leftPosTag);
      if( matcher.find() ) {
        leftPosTagExtra += matcher.group();
        leftPosTag = matcher.replaceAll("");
      }
      if( leftPosTag.contains(COMPB_TAG) ) {
        leftPosTag = leftPosTag.replace(COMPB_TAG, "");
      }

      for (AnalyzedToken rightAnalyzedToken : rightAnalyzedTokens) {
        String rightPosTag = rightAnalyzedToken.getPOSTag();
        
        if( rightPosTag == null )
          continue;

        String extraNvTag = "";
        boolean rightNv = false;
        if( rightPosTag.contains(NV_TAG) ) {
          rightNv = true;
          
          if( leftNv ) {
            extraNvTag += NV_TAG;
          }
        }

        Matcher matcherR = EXTRA_TAGS.matcher(rightPosTag);
        if( matcherR.find() ) {
          rightPosTag = matcherR.replaceAll("");
        }
        if( rightPosTag.contains(COMPB_TAG) ) {
          rightPosTag = rightPosTag.replace(COMPB_TAG, "");
        }
        
        if (leftPosTag.equals(rightPosTag) 
            && IPOSTag.startsWith(leftPosTag, IPOSTag.numr, IPOSTag.adv, IPOSTag.adj, IPOSTag.excl, IPOSTag.verb) ) {
          newAnalyzedTokens.add(new AnalyzedToken(word, leftPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
        }
        // noun-noun
        else if ( leftPosTag.startsWith(IPOSTag.noun.getText()) && rightPosTag.startsWith(IPOSTag.noun.getText()) ) {
          String agreedPosTag = getAgreedPosTag(leftPosTag, rightPosTag, leftNv);

          if( agreedPosTag == null 
              && rightPosTag.startsWith("noun:m:v_naz")
              && isMinMax(rightAnalyzedToken.getToken()) ) {
            agreedPosTag = leftPosTag;
          }

          if( agreedPosTag == null && ! isSameAnimStatus(leftPosTag, rightPosTag) ) {

            agreedPosTag = tryAnimInanim(leftPosTag, rightPosTag, leftAnalyzedToken.getLemma(), rightAnalyzedToken.getLemma(), leftNv, rightNv);
            
            if( agreedPosTag == null ) {
              animInanimNotTagged = leftPosTag.contains(":anim") ? "anim-inanim" : "inanim-anim";
            }
            else {
              newAnalyzedTokensAnimInanim.add(new AnalyzedToken(word, agreedPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
              continue;
            }
          }
          
          if( agreedPosTag != null ) {
            newAnalyzedTokens.add(new AnalyzedToken(word, agreedPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
          }
        }
        // numr-numr: один-два
        else if ( leftPosTag.startsWith(IPOSTag.numr.getText()) && rightPosTag.startsWith(IPOSTag.numr.getText()) ) {
            String agreedPosTag = getNumAgreedPosTag(leftPosTag, rightPosTag, leftNv);
            if( agreedPosTag != null ) {
              newAnalyzedTokens.add(new AnalyzedToken(word, agreedPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
            }
        }
        // noun-numr match
        else if ( IPOSTag.startsWith(leftPosTag, IPOSTag.noun) && IPOSTag.startsWith(rightPosTag, IPOSTag.numr) ) {
          // gender tags match
          String leftGenderConj = PosTagHelper.getGenderConj(leftPosTag);
          if( leftGenderConj != null && leftGenderConj.equals(PosTagHelper.getGenderConj(rightPosTag)) ) {
            newAnalyzedTokens.add(new AnalyzedToken(word, leftPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
          }
          else {
            // (with different gender tags): сотні (:p:) - дві (:f:)
            String agreedPosTag = getNumAgreedPosTag(leftPosTag, rightPosTag, leftNv);
            if( agreedPosTag != null ) {
              newAnalyzedTokens.add(new AnalyzedToken(word, agreedPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
            }
          }
        }
        // noun-adj match: Буш-молодший, братів-православних, рік-два
        else if( leftPosTag.startsWith(IPOSTag.noun.getText()) 
            && IPOSTag.startsWith(rightPosTag, IPOSTag.adj, IPOSTag.numr) ) {
          String leftGenderConj = PosTagHelper.getGenderConj(leftPosTag);
          if( leftGenderConj != null && leftGenderConj.equals(PosTagHelper.getGenderConj(rightPosTag)) ) {
            newAnalyzedTokens.add(new AnalyzedToken(word, leftPosTag + extraNvTag + leftPosTagExtra, leftAnalyzedToken.getLemma() + "-" + rightAnalyzedToken.getLemma()));
          }
        }
      }
    }
    
    if( newAnalyzedTokens.isEmpty() ) {
      newAnalyzedTokens = newAnalyzedTokensAnimInanim;
    }

    if( animInanimNotTagged != null && newAnalyzedTokens.isEmpty() ) {
      debug_compound_unknown_write(word + " " + animInanimNotTagged);
    }
    
    return newAnalyzedTokens.isEmpty() ? null : newAnalyzedTokens;
  }

  private static boolean isMinMax(String rightToken) {
    return rightToken.equals("максимум")
        || rightToken.equals("мінімум");
  }

  private String tryAnimInanim(String leftPosTag, String rightPosTag, String leftLemma, String rightLemma, boolean leftNv, boolean rightNv) {
    String agreedPosTag = null;
    
    // підприємство-банкрут
    if( leftMasterSet.contains(leftLemma) ) {
      if( leftPosTag.contains(TAG_ANIM) ) {
        rightPosTag = rightPosTag.concat(TAG_ANIM);
      }
      else {
        rightPosTag = rightPosTag.replace(TAG_ANIM, "");
      }
      
      agreedPosTag = getAgreedPosTag(leftPosTag, rightPosTag, leftNv);
      
      if( agreedPosTag == null ) {
        if (! leftPosTag.contains(TAG_ANIM)) {
          if (MNP_ZNA_REGEX.matcher(leftPosTag).matches() && MNP_NAZ_REGEX.matcher(rightPosTag).matches()
              && ! leftNv && ! rightNv ) {
            agreedPosTag = leftPosTag;
          }
        }
        else {
          if (MNP_ZNA_REGEX.matcher(leftPosTag).matches() && MNP_ROD_REGEX.matcher(rightPosTag).matches()
              && ! leftNv && ! rightNv ) {
            agreedPosTag = leftPosTag;
          }
        }
      }
      
    }
    // сонях-красень
    else if ( slaveSet.contains(rightLemma) ) {
      rightPosTag = rightPosTag.replace(":anim", "");
      agreedPosTag = getAgreedPosTag(leftPosTag, rightPosTag, false);
      if( agreedPosTag == null ) {
        if (! leftPosTag.contains(TAG_ANIM)) {
          if (MNP_ZNA_REGEX.matcher(leftPosTag).matches() && MNP_NAZ_REGEX.matcher(rightPosTag).matches()
              && PosTagHelper.getNum(leftPosTag).equals(PosTagHelper.getNum(rightPosTag))
              && ! leftNv && ! rightNv ) {
            agreedPosTag = leftPosTag;
          }
        }
      }
    }
    // красень-сонях
    else if ( slaveSet.contains(leftLemma) ) {
      leftPosTag = leftPosTag.replace(":anim", "");
      agreedPosTag = getAgreedPosTag(rightPosTag, leftPosTag, false);
      if( agreedPosTag == null ) {
        if (! rightPosTag.contains(TAG_ANIM)) {
          if (MNP_ZNA_REGEX.matcher(rightPosTag).matches() && MNP_NAZ_REGEX.matcher(leftPosTag).matches()
              && PosTagHelper.getNum(leftPosTag).equals(PosTagHelper.getNum(rightPosTag))
              && ! leftNv && ! rightNv ) {
            agreedPosTag = rightPosTag;
          }
        }
      }
    }
    // else
    // рослин-людожерів, слалому-гіганту, місяця-князя, депутатів-привидів
    
    return agreedPosTag;
  }

  // right part is numr
  private String getNumAgreedPosTag(String leftPosTag, String rightPosTag, boolean leftNv) {
    String agreedPosTag = null;
    
    if( leftPosTag.contains(":p:") && SING_REGEX_F.matcher(rightPosTag).find()
        || SING_REGEX_F.matcher(leftPosTag).find() && rightPosTag.contains(":p:")) {
      if( PosTagHelper.getConj(leftPosTag).equals(PosTagHelper.getConj(rightPosTag)) ) {
        agreedPosTag = leftPosTag;
      }
    }
    return agreedPosTag;
  }

  @Nullable
  private String getAgreedPosTag(String leftPosTag, String rightPosTag, boolean leftNv) {
    if( isPlural(leftPosTag) && ! isPlural(rightPosTag)
        || ! isPlural(leftPosTag) && isPlural(rightPosTag) )
      return null;
    
    if( ! isSameAnimStatus(leftPosTag, rightPosTag) )
      return null;
    
    if( stdNounTagRegex.matcher(leftPosTag).matches() ) {
      if (stdNounTagRegex.matcher(rightPosTag).matches()) {
        String substring1 = leftPosTag.substring(stdNounTagLen, stdNounTagLen + 3);
        String substring2 = rightPosTag.substring(stdNounTagLen, stdNounTagLen + 3);
        if( substring1.equals(substring2) ) {
          if( leftNv )
            return rightPosTag;

          return leftPosTag;
        }
      }
    }

    return null;
  }

  private static boolean isSameAnimStatus(String leftPosTag, String rightPosTag) {
    return leftPosTag.contains(TAG_ANIM) && rightPosTag.contains(TAG_ANIM)
        || ! leftPosTag.contains(TAG_ANIM) && ! rightPosTag.contains(TAG_ANIM);
  }

  private static boolean isPlural(String posTag) {
    return posTag.startsWith("noun:p:");
  }

  private List<AnalyzedToken> oAdjMatch(String word, List<AnalyzedToken> analyzedTokens, String leftWord) {
    List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>(analyzedTokens.size());

    String leftBase = leftWord.substring(0, leftWord.length()-1);
    if( ! LEFT_O_ADJ.contains(leftWord.toLowerCase(conversionLocale))
        && tagBothCases(leftWord).isEmpty()            // яскраво для яскраво-барвистий
        && tagBothCases(oToYj(leftWord)).isEmpty()  // кричущий для кричуще-яскравий
        && tagBothCases(leftBase).isEmpty()         // паталог для паталого-анатомічний
        && tagBothCases(leftBase + "а").isEmpty() ) // два для дво-триметровий
      return null;
    
    for (AnalyzedToken analyzedToken : analyzedTokens) {
      String posTag = analyzedToken.getPOSTag();
      if( posTag.startsWith( IPOSTag.adj.getText() ) ) {
        newAnalyzedTokens.add(new AnalyzedToken(word, posTag, leftWord + "-" + analyzedToken.getLemma()));
      }
    }
    
    return newAnalyzedTokens.isEmpty() ? null : newAnalyzedTokens;
  }

  private static String oToYj(String leftWord) {
    return leftWord.endsWith("ьо") 
        ? leftWord.substring(0, leftWord.length()-2) + "ій" 
        : leftWord.substring(0,  leftWord.length()-1) + "ий";
  }

  private List<AnalyzedToken> getNvPrefixNounMatch(String word, List<AnalyzedToken> analyzedTokens, String leftWord) {
    List<AnalyzedToken> newAnalyzedTokens = new ArrayList<>(analyzedTokens.size());
    
    for (AnalyzedToken analyzedToken : analyzedTokens) {
      String posTag = analyzedToken.getPOSTag();
      if( posTag.startsWith( IPOSTag.noun.getText() ) ) {
        newAnalyzedTokens.add(new AnalyzedToken(word, posTag, leftWord + "-" + analyzedToken.getLemma()));
      }
    }
    
    return newAnalyzedTokens.isEmpty() ? null : newAnalyzedTokens;
  }

  @Nullable
  private List<AnalyzedToken> poAdvMatch(String word, List<AnalyzedToken> analyzedTokens, String adjTag) {
    
    for (AnalyzedToken analyzedToken : analyzedTokens) {
      String posTag = analyzedToken.getPOSTag();
      if( posTag.startsWith( adjTag ) ) {
        return Arrays.asList(new AnalyzedToken(word, IPOSTag.adv.getText(), word));
      }
    }
    
    return null;
  }

  // methods for debugging compounds

  private void debugCompounds() {
    try {
      Path unknownFile = Paths.get("compounds-unknown.txt");
      Files.deleteIfExists(unknownFile);
      unknownFile = Files.createFile(unknownFile);
      compoundUnknownDebugWriter = Files.newBufferedWriter(unknownFile, Charset.defaultCharset());

      Path taggedFile = Paths.get("compounds-tagged.txt");
      Files.deleteIfExists(taggedFile);
      taggedFile = Files.createFile(taggedFile);
      compoundTaggedDebugWriter = Files.newBufferedWriter(taggedFile, Charset.defaultCharset());

//      Path tagged2File = Paths.get("tagged.txt");
//      Files.deleteIfExists(tagged2File);
//      taggedFile = Files.createFile(tagged2File);
//      taggedDebugWriter = Files.newBufferedWriter(tagged2File, Charset.defaultCharset());
    } catch (IOException ex) {
      throw new RuntimeException(ex);
    }
  }

  private void debug_compound_unknown_write(String word) {
    if( compoundUnknownDebugWriter == null )
      return;
    
    try {
      compoundUnknownDebugWriter.append(word);
      compoundUnknownDebugWriter.newLine();
      compoundUnknownDebugWriter.flush();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  protected List<AnalyzedToken> getAnalyzedTokens(String word) {
    List<AnalyzedToken> tkns = super.getAnalyzedTokens(word);

    if( tkns.get(0).getPOSTag() == null ) {
      if( (word.indexOf('\u2013') != -1) 
           && word.matches(".*[а-яіїєґ][\u2013][а-яіїєґ].*")) {
        String newWord = word.replace('\u2013', '-');
        
        List<AnalyzedToken> newTokens = super.getAnalyzedTokens(newWord);
        
        for (int i = 0; i < newTokens.size(); i++) {
          AnalyzedToken analyzedToken = newTokens.get(i);
          if( newWord.equals(analyzedToken.getToken()) ) {
            String lemma = analyzedToken.getLemma();
            if( lemma != null ) {
              lemma = lemma.replace('-', '\u2013');
            }
            AnalyzedToken newToken = new AnalyzedToken(word, analyzedToken.getPOSTag(), lemma);
            newTokens.set(i, newToken);
          }
        }
        
        tkns = newTokens;
      }
    }
    
    if( taggedDebugWriter != null && ! tkns.isEmpty() ) {
      debug_tagged_write(tkns, taggedDebugWriter);
    }
    
    return tkns;
  }

  private void debug_compound_tagged_write(List<AnalyzedToken> guessedCompoundTags) {
    if( compoundTaggedDebugWriter == null || guessedCompoundTags == null )
      return;

    debug_tagged_write(guessedCompoundTags, compoundTaggedDebugWriter);
  }
  
  private void debug_tagged_write(List<AnalyzedToken> analyzedTokens, BufferedWriter writer) {
    if( analyzedTokens.get(0).getLemma() == null || analyzedTokens.get(0).getToken().trim().isEmpty() )
          return;

    try {
      String prevToken = "";
      String prevLemma = "";
      for (AnalyzedToken analyzedToken : analyzedTokens) {
        String token = analyzedToken.getToken();
        
        boolean firstTag = false;
        if (! prevToken.equals(token)) {
          if( prevToken.length() > 0 ) {
            writer.append(";  ");
            prevLemma = "";
          }
          writer.append(token).append(" ");
          prevToken = token;
          firstTag = true;
        }
        
        String lemma = analyzedToken.getLemma();

        if (! prevLemma.equals(lemma)) {
          if( prevLemma.length() > 0 ) {
            writer.append(", ");
          }
          writer.append(lemma); //.append(" ");
          prevLemma = lemma;
          firstTag = true;
        }

        writer.append(firstTag ? " " : "|").append(analyzedToken.getPOSTag());
        firstTag = false;
      }
      writer.newLine();
      writer.flush();
    } catch (IOException e) {
      throw new RuntimeException(e);
    }
  }

  
}


File: languagetool-language-modules/uk/src/main/java/org/languagetool/tokenizers/uk/UkrainianWordTokenizer.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2005 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.tokenizers.uk;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import java.util.StringTokenizer;

import org.languagetool.tokenizers.Tokenizer;

/**
 * Tokenizes a sentence into words.
 * Punctuation and whitespace gets its own token.
 * Specific to Ukrainian: apostrophes (0x27 and U+2019) not in the list as they are part of the word
 * 
 * @author Andriy Rysin
 */
public class UkrainianWordTokenizer implements Tokenizer {
  private static final String SPLIT_CHARS = "\u0020\u00A0\u115f\u1160\u1680" 
        + "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007" 
        + "\u2008\u2009\u200A\u200B\u200c\u200d\u200e\u200f"
        + "\u2028\u2029\u202a\u202b\u202c\u202d\u202e\u202f"
        + "\u205F\u2060\u2061\u2062\u2063\u206A\u206b\u206c\u206d"
        + "\u206E\u206F\u3000\u3164\ufeff\uffa0\ufff9\ufffa\ufffb" 
        + ",.;()[]{}<>!?:/|\\\"«»„”“`´‘‛′…¿¡\t\n\r\uE100";

  // decimal comma between digits
  private static final Pattern DECIMAL_COMMA_PATTERN = Pattern.compile("([\\d]),([\\d])", Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE);
  private static final char DECIMAL_COMMA_SUBST = '\uE001'; // some unused character to hide comma in decimal number temporary for tokenizer run
  // space between digits
//  private static final Pattern DECIMAL_SPACE_PATTERN = Pattern.compile("([\\d]{1,3})( ([\\d]{3}))+", Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE);
//  private static final char DECIMAL_SPACE_SUBST = '\uE008';
  // dots in numbers
  private static final Pattern DOTTED_NUMBERS_PATTERN = Pattern.compile("([\\d])\\.([\\d])", Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE);
  private static final char NUMBER_DOT_SUBST = '\uE002';
  // colon in numbers
  private static final Pattern COLON_NUMBERS_PATTERN = Pattern.compile("([\\d]):([\\d])", Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE);
  private static final char COLON_DOT_SUBST = '\uE003';
  // dates
  private static final Pattern DATE_PATTERN = Pattern.compile("([\\d]{2})\\.([\\d]{2})\\.([\\d]{4})|([\\d]{4})\\.([\\d]{2})\\.([\\d]{2})|([\\d]{4})-([\\d]{2})-([\\d]{2})", Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE);
  private static final char DATE_DOT_SUBST = '\uE004'; // some unused character to hide dot in date temporary for tokenizer run
  // braces in words
  private static final Pattern BRACE_IN_WORD_PATTERN = Pattern.compile("([а-яіїєґ'])\\(([а-яіїєґ']+)\\)", Pattern.CASE_INSENSITIVE|Pattern.UNICODE_CASE);
  private static final char LEFT_BRACE_SUBST = '\uE005';
  private static final char RIGHT_BRACE_SUBST = '\uE006';
  // abbreviation dot
  //TODO: also use abbreviation list to allow next letter to be capital
  private static final Pattern ABBR_DOT_PATTERN = Pattern.compile("([а-яіїєґ])\\. ([а-яіїєґ])");
  private static final Pattern ABBR_DOT_PATTERN2 = Pattern.compile("([Аа]кад|[Пп]роф|[Дд]оц|[Аа]сист|с|м|вул|о|р|ім)\\.\\s([А-ЯІЇЄҐ])");
  private static final char ABBR_DOT_SUBST = '\uE007';
  // ellipsis
  private static final String ELLIPSIS = "...";
  private static final String ELLIPSIS_SUBST = "\uE100";


  public UkrainianWordTokenizer() {
  }

  @Override
  public List<String> tokenize(String text) {
    text = cleanup(text);
    
    if( text.contains(",") ) {
      text = DECIMAL_COMMA_PATTERN.matcher(text).replaceAll("$1" + DECIMAL_COMMA_SUBST + "$2");
    }
    
    if( text.contains(".") ) {
      text = DATE_PATTERN.matcher(text).replaceAll("$1" + DATE_DOT_SUBST + "$2" + DATE_DOT_SUBST + "$3");
      text = DOTTED_NUMBERS_PATTERN.matcher(text).replaceAll("$1" + NUMBER_DOT_SUBST + "$2");
      text = ABBR_DOT_PATTERN.matcher(text).replaceAll("$1" + ABBR_DOT_SUBST + " $2");
      text = ABBR_DOT_PATTERN2.matcher(text).replaceAll("$1" + ABBR_DOT_SUBST + " $2");
    }

    if( text.contains(":") ) {
      text = COLON_NUMBERS_PATTERN.matcher(text).replaceAll("$1" + COLON_DOT_SUBST + "$2");
    }

    if( text.contains("(") ) {
      text = BRACE_IN_WORD_PATTERN.matcher(text).replaceAll("$1" + LEFT_BRACE_SUBST + "$2" + RIGHT_BRACE_SUBST);
    }

//    if( text.contains(" ") ) {
//      text = DECIMAL_SPACE_PATTERN.matcher(text).replaceAll("$1" + DECIMAL_SPACE_SUBST + "$2");
//    }
    
    if( text.contains(ELLIPSIS) ) {
      text = text.replace(ELLIPSIS, ELLIPSIS_SUBST);
    }
    
    List<String> tokenList = new ArrayList<>();
    StringTokenizer st = new StringTokenizer(text, SPLIT_CHARS, true);

    while (st.hasMoreElements()) {
      String token = st.nextToken();
      
      token = token.replace(DECIMAL_COMMA_SUBST, ',');
      
      //TODO: merge all dots to speed things up ???
      token = token.replace(DATE_DOT_SUBST, '.');
      token = token.replace(NUMBER_DOT_SUBST, '.');
      token = token.replace(ABBR_DOT_SUBST, '.');
      
      token = token.replace(COLON_DOT_SUBST, ':');
      token = token.replace(LEFT_BRACE_SUBST, '(');
      token = token.replace(RIGHT_BRACE_SUBST, ')');
      token = token.replaceAll(ELLIPSIS_SUBST, ELLIPSIS);

      tokenList.add( token );
    }

    return tokenList;
  }

  private static String cleanup(String text) {
    text = text.replace('’', '\'').replace('ʼ', '\'');

//    if( text.contains("\u0301") || text.contains("\u00AD") ) {
//      text = text.replace("\u0301", "").replace("\u00AD", "");
//    }

//    while( text.contains("\u0301") || text.contains("\u00AD") ) {
//      text = IGNORE_CHARS_PATTERN.matcher(text).replaceAll("$1$3");
//    }

    return text;
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/rules/uk/MixedAlphabetsRuleTest.java
/* LanguageTool, a natural language style checker
 * Copyright (C) 2013 Andriy Rysin
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.rules.uk;

import org.junit.Test;
import org.languagetool.JLanguageTool;
import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.rules.RuleMatch;

import java.io.IOException;
import java.util.Arrays;

import static org.junit.Assert.assertEquals;

public class MixedAlphabetsRuleTest {

  @Test
  public void testRule() throws IOException {
    final MixedAlphabetsRule rule = new MixedAlphabetsRule(TestTools.getMessages("uk"));
    final JLanguageTool langTool = new JLanguageTool(new Ukrainian());

    // correct sentences:
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("сміття")).length);
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("not mixed")).length);
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("123454")).length);

    //incorrect sentences:

    RuleMatch[] matches = rule.match(langTool.getAnalyzedSentence("смiття"));  //latin i
    // check match positions:
    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("сміття"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("mіхed"));  // cyrillic i and x

    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("mixed"), matches[0].getSuggestedReplacements());
    
    matches = rule.match(langTool.getAnalyzedSentence("XІ")); // cyrillic І and latin X

    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("XI"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("ХI")); // cyrillic X and latin I

    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("XI"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("ХІ")); // cyrillic both X and I used for latin number

    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("XI"), matches[0].getSuggestedReplacements());
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/rules/uk/MorfologikUkrainianSpellerRuleTest.java
/* LanguageTool, a natural language style checker
 * Copyright (C) 2012 Marcin Miłkowski
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.rules.uk;

import static org.junit.Assert.assertEquals;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;

import org.junit.Test;
import org.languagetool.JLanguageTool;
import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.rules.RuleMatch;

public class MorfologikUkrainianSpellerRuleTest {

  @Test
  public void testMorfologikSpeller() throws IOException {
    MorfologikUkrainianSpellerRule rule = new MorfologikUkrainianSpellerRule (TestTools.getMessages("uk"), new Ukrainian());

    JLanguageTool langTool = new JLanguageTool(new Ukrainian());

    // correct sentences:
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("До вас прийде заввідділу!")).length);
    assertEquals(0, rule.match(langTool.getAnalyzedSentence(",")).length);
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("123454")).length);

    assertEquals(0, rule.match(langTool.getAnalyzedSentence("До нас приїде The Beatles!")).length);

    // soft hyphen
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("піс\u00ADні")).length);
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("піс\u00ADні піс\u00ADні")).length);
    
    
    //incorrect sentences:

    RuleMatch[] matches = rule.match(langTool.getAnalyzedSentence("атакуючий"));
    // check match positions:
    assertEquals(1, matches.length);

    matches = rule.match(langTool.getAnalyzedSentence("шкляний"));

    assertEquals(1, matches.length);
    assertEquals("скляний", matches[0].getSuggestedReplacements().get(0));

    assertEquals(0, rule.match(langTool.getAnalyzedSentence("а")).length);

    // mix alphabets
    matches = rule.match(langTool.getAnalyzedSentence("прийдешнiй"));   // latin 'i'

    assertEquals(1, matches.length);
    assertEquals("прийдешній", matches[0].getSuggestedReplacements().get(0));

    // compounding
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("Жакет був синьо-жовтого кольору")).length);

    assertEquals(0, rule.match(langTool.getAnalyzedSentence("Він багато сидів на інтернет-форумах")).length);

    assertEquals(1, rule.match(langTool.getAnalyzedSentence("Він багато сидів на інтермет-форумах")).length);

    // dynamic tagging
    assertEquals(0, rule.match(langTool.getAnalyzedSentence("екс-креветка")).length);


    // abbreviations

    RuleMatch[] match = rule.match(langTool.getAnalyzedSentence("Читання віршів Т.Г.Шевченко і Г.Тютюнника"));
    assertEquals(new ArrayList<RuleMatch>(), Arrays.asList(match));

    match = rule.match(langTool.getAnalyzedSentence("Читання віршів Т. Г. Шевченко і Г. Тютюнника"));
    assertEquals(new ArrayList<RuleMatch>(), Arrays.asList(match));

    match = rule.match(langTool.getAnalyzedSentence("Англі́йська мова (англ. English language, English) належить до германської групи"));
    assertEquals(new ArrayList<RuleMatch>(), Arrays.asList(match));

    match = rule.match(langTool.getAnalyzedSentence("Англі́йська мова (англ English language, English) належить до германської групи"));
    assertEquals(1, match.length);
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/rules/uk/SimpleReplaceRuleTest.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2005 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */

package org.languagetool.rules.uk;

import junit.framework.TestCase;
import org.languagetool.JLanguageTool;
import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.rules.RuleMatch;

import java.io.IOException;
import java.util.Arrays;


public class SimpleReplaceRuleTest extends TestCase {

  public void testRule() throws IOException {
    SimpleReplaceRule rule = new SimpleReplaceRule(TestTools.getEnglishMessages());

    RuleMatch[] matches;
    JLanguageTool langTool = new JLanguageTool(new Ukrainian());

    // correct sentences:
    matches = rule.match(langTool.getAnalyzedSentence("Ці рядки повинні збігатися."));
    assertEquals(0, matches.length);

    // incorrect sentences:
    matches = rule.match(langTool.getAnalyzedSentence("Ці рядки повинні співпадати."));
    assertEquals(1, matches.length);
    assertEquals(2, matches[0].getSuggestedReplacements().size());
    assertEquals(Arrays.asList("збігатися", "сходитися"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("Нападаючий"));
    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("Нападник", "Нападальний", "Нападний"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("Нападаючого"));
    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("Нападник", "Нападальний", "Нападний"), matches[0].getSuggestedReplacements());

    // test ignoreTagged
    matches = rule.match(langTool.getAnalyzedSentence("щедрота"));
    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("щедрість", "гойність", "щедриня"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("щедроти"));
    assertEquals(0, matches.length);
  }
}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/rules/uk/TokenAgreementRuleTest.java
/* LanguageTool, a natural language style checker
 * Copyright (C) 2013 Andriy Rysin
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.rules.uk;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import org.junit.Before;
import org.junit.Test;
import org.languagetool.AnalyzedSentence;
import org.languagetool.JLanguageTool;
import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.rules.RuleMatch;

public class TokenAgreementRuleTest {

  private JLanguageTool langTool;
  private TokenAgreementRule rule;

  @Before
  public void setUp() throws IOException {
    rule = new TokenAgreementRule(TestTools.getMessages("uk"));
    langTool = new JLanguageTool(new Ukrainian());
  }
  
  @Test
  public void testRule() throws IOException {

    // correct sentences:
    assertEmptyMatch("без повного");
    assertEmptyMatch("без неба");

    assertEmptyMatch("по авеню");

    assertEmptyMatch("що за ганебна непослідовність?");

    assertEmptyMatch("щодо власне людини");
    assertEmptyMatch("у загалом симпатичній повістині");

    assertEmptyMatch("понад половина людей");
    assertEmptyMatch("з понад ста людей");

    assertEmptyMatch("по нервах");
    assertEmptyMatch("з особливою увагою");

    assertEmptyMatch("щодо бодай гіпотетичної здатності");
    assertEmptyMatch("хто їде на заробітки за кордон");

    assertEmptyMatch("піти в президенти");
    assertEmptyMatch("піти межі люди");

    assertEmptyMatch("що то була за людина");
    assertEmptyMatch("що за людина");
    assertEmptyMatch("що балотувався за цім округом");

    assertEmptyMatch("на дому");

    assertEmptyMatch("окрім як українці");
    assertEmptyMatch("за двісті метрів");
    assertEmptyMatch("переходить у Фрідріх Штрассе");
    assertEmptyMatch("від мінус 1 до плюс 1");
    assertEmptyMatch("до мінус сорока град");
    assertEmptyMatch("до мінус шістдесяти");
    assertEmptyMatch("через років 10");
    assertEmptyMatch("на хвилин 9-10");
    assertEmptyMatch("співпрацювати із собі подібними");
    assertEmptyMatch("через усім відомі причини");
    assertEmptyMatch("через нікому не відомі причини");
    assertEmptyMatch("прийшли до ВАТ «Кривий Ріг цемент»");
    assertEmptyMatch("від А до Я");
    assertEmptyMatch("до та після");
    assertEmptyMatch("до схід сонця");
    assertEmptyMatch("з рана до вечора, від рана до ночі");
    assertEmptyMatch("до НАК «Надра України»");
    assertEmptyMatch("призвів до значною мірою демократичного середнього класу");
    assertEmptyMatch("Вони замість Андрій вибрали Юрій");
    assertEmptyMatch("на мохом стеленому дні");
    assertEmptyMatch("час від часу нам доводилось");
    assertEmptyMatch("який до речі вони присягалися");
    assertEmptyMatch("ні до чого доброго силові дії не призведуть");
//    assertEmptyMatch("Імена від Андрій до Юрій");  // називний між від і до рідко зустрічається але такий виняток ховає багато помилок 

    assertEquals(1, rule.match(langTool.getAnalyzedSentence("призвів до значною мірою демократичному середньому класу")).length);

//    assertEmptyMatch("як у Конана Дойла")).length); //TODO
//    assertEmptyMatch("як у Конану Дойла")).length);
//    assertEmptyMatch("як у Конан Дойла")).length);
    
    //incorrect sentences:

    RuleMatch[] matches = rule.match(langTool.getAnalyzedSentence("без небу"));
    // check match positions:
    assertEquals(1, matches.length);
    assertEquals(Arrays.asList("неба"), matches[0].getSuggestedReplacements());

    matches = rule.match(langTool.getAnalyzedSentence("не в останню чергу через    корупцією, міжрелігійну ворожнечу"));
    assertEquals(1, matches.length);

    matches = rule.match(langTool.getAnalyzedSentence("по нервам"));
    // check match positions:
    assertEquals(1, matches.length);
    assertEquals(3, matches[0].getFromPos());
    assertEquals(9, matches[0].getToPos());
    assertEquals(Arrays.asList("нервах", "нерви"), matches[0].getSuggestedReplacements());
    
    assertEquals(1, rule.match(langTool.getAnalyzedSentence("в п'ятьом людям")).length);
    assertEquals(1, rule.match(langTool.getAnalyzedSentence("в понад п'ятьом людям")).length);

    AnalyzedSentence analyzedSentence = langTool.getAnalyzedSentence("завдяки їх вдалим трюкам");
    RuleMatch[] match = rule.match(analyzedSentence);
    assertEquals(1, match.length);
    List<String> suggestedReplacements = match[0].getSuggestedReplacements();
    assertTrue("Did not find «їхній»: " + suggestedReplacements, suggestedReplacements.contains("їхнім"));

    analyzedSentence = langTool.getAnalyzedSentence("О дівчина!");
    match = rule.match(analyzedSentence);
    assertEquals(1, match.length);
    suggestedReplacements = match[0].getSuggestedReplacements();
    assertTrue("Did not find кличний «дівчино»: " + suggestedReplacements, suggestedReplacements.contains("дівчино"));

    matches = rule.match(langTool.getAnalyzedSentence("по церковним канонам"));
    // check match positions:
    assertEquals(1, matches.length);

    // свята
    assertEmptyMatch("на Купала");
    assertEmptyMatch("на Явдохи");
    // вулиці
    assertEmptyMatch("на Мазепи");
    assertEmptyMatch("на Кульчицької");
    assertEmptyMatch("на Правди");
    assertEmptyMatch("на Ломоносова");
    // invert
    assertEmptyMatch("як на Кучми іменини");

    assertEmptyMatch("спиралося на місячної давнини рішення");
    assertEmptyMatch("На середньої довжини шубу");

    matches = rule.match(langTool.getAnalyzedSentence("спиралося на місячної давнини рішенням"));
    assertEquals(1, matches.length);

    matches = rule.match(langTool.getAnalyzedSentence("Від стягу Ататюрка до піратського прапору"));
    assertEquals(1, matches.length);

    matches = rule.match(langTool.getAnalyzedSentence("згідно з документа"));
    assertEquals(1, matches.length);

//    matches = rule.match(langTool.getAnalyzedSentence("колега з Мінську"));
//    System.out.println(langTool.getAnalyzedSentence("колега з Мінську"));
//    // check match positions:
//    assertEquals(1, matches.length);

  }

  private void assertEmptyMatch(String text) throws IOException {
    assertEquals(Collections.<RuleMatch>emptyList(), Arrays.asList(rule.match(langTool.getAnalyzedSentence(text))));
  }
  
  @Test
  public void testSpecialChars() throws IOException {
    TokenAgreementRule rule = new TokenAgreementRule(TestTools.getMessages("uk"));

    JLanguageTool langTool = new JLanguageTool(new Ukrainian());

    RuleMatch[] matches = rule.match(langTool.getAnalyzedSentence("по не́рвам, по мо\u00ADстам, по воротам"));
    // check match positions:
    assertEquals(3, matches.length);

    assertEmptyMatch("до їм поді\u00ADбних");

    assertEquals(3, matches[0].getFromPos());
    assertEquals(10, matches[0].getToPos());
    assertEquals(Arrays.asList("нервах", "нерви"), matches[0].getSuggestedReplacements());
//    assertEquals(3, matches[1].getFromPos());

    assertEquals(15, matches[1].getFromPos());
    assertEquals(Arrays.asList("мостах", "мости"), matches[1].getSuggestedReplacements());
//    assertEquals(1, matches[1].getFromPos());

    assertEquals(27, matches[2].getFromPos());
    assertEquals(Arrays.asList("воротах", "ворота"), matches[2].getSuggestedReplacements());
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/rules/uk/UkrainianWordRepeatRuleTest.java
/* LanguageTool, a natural language style checker
 * Copyright (C) 2013 Daniel Naber (http://www.danielnaber.de)
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.rules.uk;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;

import org.junit.Before;
import org.junit.Test;
import org.languagetool.JLanguageTool;
import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.rules.RuleMatch;

import static org.junit.Assert.assertEquals;

public class UkrainianWordRepeatRuleTest {
  
  private JLanguageTool langTool;
  private UkrainianWordRepeatRule rule;

  @Before
  public void setUp() throws IOException {
    langTool = new JLanguageTool(new Ukrainian());
    rule = new UkrainianWordRepeatRule(TestTools.getMessages("uk"), langTool.getLanguage());
  }
  
  @Test
  public void testRule() throws IOException {
    assertEmptyMatch("без повного розрахунку");
    assertEmptyMatch("без бугіма бугіма");
    assertEmptyMatch("без 100 100");
    assertEmptyMatch("1.30 3.20 3.20");
    assertEmptyMatch("ще в В.Кандинського");
    assertEmptyMatch("Від добра добра не шукають.");
    assertEmptyMatch("Що що, а кіно в Україні...");

    assertEquals(1, rule.match(langTool.getAnalyzedSentence("без без повного розрахунку")).length);
    RuleMatch[] match = rule.match(langTool.getAnalyzedSentence("Верховної Ради І і ІІ скликань"));
    assertEquals(1, match.length);
    assertEquals(2, match[0].getSuggestedReplacements().size());
  }

  private void assertEmptyMatch(String text) throws IOException {
    assertEquals(text, Collections.<RuleMatch>emptyList(), Arrays.asList(rule.match(langTool.getAnalyzedSentence(text))));
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/tagging/uk/UkrainianTaggerTest.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2006 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */
package org.languagetool.tagging.uk;

import java.io.IOException;

import junit.framework.TestCase;

import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.tokenizers.uk.UkrainianWordTokenizer;

public class UkrainianTaggerTest extends TestCase {
    
  private UkrainianTagger tagger;
  private UkrainianWordTokenizer tokenizer;
      
  @Override
  public void setUp() {
    tagger = new UkrainianTagger();
    tokenizer = new UkrainianWordTokenizer();
  }

  public void testDictionary() throws IOException {
    TestTools.testDictionary(tagger, new Ukrainian());
  }
  
  public void testTagger() throws IOException {

    // one-way case sensitivity
    TestTools.myAssert("києві", "києві/[кий]noun:m:v_dav", tokenizer, tagger);
    TestTools.myAssert("Києві", "Києві/[Київ]noun:m:v_mis|Києві/[кий]noun:m:v_dav", tokenizer, tagger);
    TestTools.myAssert("віл", "віл/[віл]noun:m:v_naz:anim", tokenizer, tagger);
    TestTools.myAssert("Віл", "Віл/[віл]noun:m:v_naz:anim", tokenizer, tagger);
    TestTools.myAssert("ВІЛ", "ВІЛ/[ВІЛ]noun:m:v_dav:nv:np:abbr|ВІЛ/[ВІЛ]noun:m:v_mis:nv:np:abbr|ВІЛ/[ВІЛ]noun:m:v_naz:nv:np:abbr|ВІЛ/[ВІЛ]noun:m:v_oru:nv:np:abbr|ВІЛ/[ВІЛ]noun:m:v_rod:nv:np:abbr|ВІЛ/[ВІЛ]noun:m:v_zna:nv:np:abbr|ВІЛ/[віл]noun:m:v_naz:anim", tokenizer, tagger);
    TestTools.myAssert("далі", "далі/[далі]adv", tokenizer, tagger);
    TestTools.myAssert("Далі", "Далі/[Даль]noun:m:v_mis:anim:lname|Далі/[Далі]noun:m:v_dav:nv:np:anim:lname|Далі/[Далі]noun:m:v_mis:nv:np:anim:lname|Далі/[Далі]noun:m:v_naz:nv:np:anim:lname|Далі/[Далі]noun:m:v_oru:nv:np:anim:lname|Далі/[Далі]noun:m:v_rod:nv:np:anim:lname|Далі/[Далі]noun:m:v_zna:nv:np:anim:lname|Далі/[далі]adv", tokenizer, tagger);
    TestTools.myAssert("Бен", "Бен/[Бен]noun:m:v_naz:anim:fname|Бен/[бен]unknown", tokenizer, tagger);
    TestTools.myAssert("бен", "бен/[бен]unknown", tokenizer, tagger);


    TestTools.myAssert("Справу порушено судом", 
      "Справу/[справа]noun:f:v_zna -- порушено/[порушити]verb:impers:perf -- судом/[суд]noun:m:v_oru|судом/[судома]noun:p:v_rod",
       tokenizer, tagger);
       
    String expected = 
      "Майже/[майже]adv -- два/[два]numr:m:v_naz|два/[два]numr:m:v_zna|два/[два]numr:n:v_naz|два/[два]numr:n:v_zna -- роки/[рік]noun:p:v_naz|роки/[рік]noun:p:v_zna"
    + " -- тому/[той]adj:m:v_dav:&pron:dem|тому/[той]adj:m:v_mis:&pron:dem|тому/[той]adj:n:v_dav:&pron:dem|тому/[той]adj:n:v_mis:&pron:dem|тому/[том]noun:m:v_dav|тому/[том]noun:m:v_mis|тому/[том]noun:m:v_rod|тому/[тому]adv|тому/[тому]conj:subord"
    + " -- Люба/[Люба]noun:f:v_naz:anim:fname|Люба/[любий]adj:f:v_naz -- разом/[раз]noun:m:v_oru|разом/[разом]adv -- із/[із]prep:rv_rod:rv_zna:rv_oru"
    + " -- чоловіком/[чоловік]noun:m:v_oru:anim -- Степаном/[Степан]noun:m:v_oru:anim:fname -- виїхали/[виїхати]verb:past:m:perf -- туди/[туди]adv:&pron:dem"
    + " -- на/[на]excl|на/[на]part|на/[на]prep:rv_zna:rv_mis -- "
    + "проживання/[проживання]noun:n:v_naz|проживання/[проживання]noun:n:v_rod|проживання/[проживання]noun:n:v_zna|проживання/[проживання]noun:p:v_naz|проживання/[проживання]noun:p:v_zna";
  
    TestTools.myAssert("Майже два роки тому Люба разом із чоловіком Степаном виїхали туди на проживання.",
        expected, tokenizer, tagger);
  }

  public void testNumberTagging() throws IOException {
    TestTools.myAssert("101,234", "101,234/[101,234]number", tokenizer, tagger);
    TestTools.myAssert("3,5-5,6% 7° 7,4°С", "3,5-5,6%/[3,5-5,6%]number -- 7°/[7°]number -- 7,4°С/[7,4°С]number", tokenizer, tagger);
    TestTools.myAssert("XIX", "XIX/[XIX]number", tokenizer, tagger);

    TestTools.myAssert("14.07.2001", "14.07.2001/[14.07.2001]date", tokenizer, tagger);

    TestTools.myAssert("о 15.33", "о/[о]excl|о/[о]prep:rv_zna:rv_mis -- 15.33/[15.33]time", tokenizer, tagger);
    TestTools.myAssert("О 1:05", "О/[о]excl|О/[о]prep:rv_zna:rv_mis -- 1:05/[1:05]time", tokenizer, tagger);
  }
  
  public void testTaggingWithDots() throws IOException {
    TestTools.myAssert("300 р. до н. е.", 
      "300/[300]number -- р./[null]null -- до/[до]noun:n:v_dav:nv|до/[до]noun:n:v_mis:nv|до/[до]noun:n:v_naz:nv|до/[до]noun:n:v_oru:nv|до/[до]noun:n:v_rod:nv|до/[до]noun:n:v_zna:nv|до/[до]noun:p:v_dav:nv|до/[до]noun:p:v_mis:nv|до/[до]noun:p:v_naz:nv|до/[до]noun:p:v_oru:nv|до/[до]noun:p:v_rod:nv|до/[до]noun:p:v_zna:nv|до/[до]prep:rv_rod -- н./[null]null -- е/[е]excl",
       tokenizer, tagger);
  
//    TestTools.myAssert("Є.Бакуліна.",
//      "Є.Бакуліна[Бакулін]noun:m:v_rod:anim:lname|Є.Бакуліна[Бакулін]noun:m:v_zna:anim:lname",
//       tokenizer, tagger);
  }
  
  public void testDynamicTagging() throws IOException {
    TestTools.myAssert("г-г-г", "г-г-г/[null]null", tokenizer, tagger);
    
    TestTools.myAssert("100-річному", "100-річному/[100-річний]adj:m:v_dav|100-річному/[100-річний]adj:m:v_mis|100-річному/[100-річний]adj:n:v_dav|100-річному/[100-річний]adj:n:v_mis", tokenizer, tagger);
    TestTools.myAssert("100-й", "100-й/[100-й]adj:m:v_naz|100-й/[100-й]adj:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("50-х", "50-х/[50-й]adj:p:v_rod|50-х/[50-й]adj:p:v_zna", tokenizer, tagger);

    TestTools.myAssert("по-свинячому", "по-свинячому/[по-свинячому]adv", tokenizer, tagger);
    TestTools.myAssert("по-сибірськи", "по-сибірськи/[по-сибірськи]adv", tokenizer, tagger);

    TestTools.myAssert("давай-но", "давай-но/[давати]verb:impr:s:2:imperf", tokenizer, tagger);
    TestTools.myAssert("дивіться-но", "дивіться-но/[дивитися]verb:rev:impr:p:2:imperf", tokenizer, tagger);
    TestTools.myAssert("той-таки", "той-таки/[той-таки]adj:m:v_naz:&pron:dem|той-таки/[той-таки]adj:m:v_zna:&pron:dem", tokenizer, tagger);
    TestTools.myAssert("буде-таки", "буде-таки/[бути]verb:futr:s:3:imperf", tokenizer, tagger);
    TestTools.myAssert("оцей-от", "оцей-от/[оцей]adj:m:v_naz:&pron:dem|оцей-от/[оцей]adj:m:v_zna:&pron:dem", tokenizer, tagger);
    TestTools.myAssert("оттакий-то", "оттакий-то/[оттакий]adj:m:v_naz:&pron:dem:rare|оттакий-то/[оттакий]adj:m:v_zna:&pron:dem:rare", tokenizer, tagger);
    TestTools.myAssert("геть-то", "геть-то/[геть]adv|геть-то/[геть]part", tokenizer, tagger);
    TestTools.myAssert("ану-бо", "ану-бо/[ану]excl|ану-бо/[ану]part", tokenizer, tagger);
    TestTools.myAssert("годі-бо", "годі-бо/[годі]predic", tokenizer, tagger);
    TestTools.myAssert("гей-но", "гей-но/[гей]excl", tokenizer, tagger);
    TestTools.myAssert("цить-но", "цить-но/[цить]excl", tokenizer, tagger);

    TestTools.myAssert("екс-партнер", "екс-партнер/[екс-партнер]noun:m:v_naz:anim", tokenizer, tagger);

    // TODO: старий -> старший
    TestTools.myAssert("Алієва-старшого", "Алієва-старшого/[Алієв-старий]noun:m:v_rod:anim:lname|Алієва-старшого/[Алієв-старий]noun:m:v_zna:anim:lname", tokenizer, tagger);

//    TestTools.myAssert("греко-уніятський", "", tokenizer, tagger);
    
    TestTools.myAssert("жило-було", "жило-було/[жити-бути]verb:past:n:imperf", tokenizer, tagger);
    TestTools.myAssert("учиш-учиш", "учиш-учиш/[учити-учити]verb:pres:s:2:imperf:v-u", tokenizer, tagger);

    TestTools.myAssert("вгору-вниз", "вгору-вниз/[вгору-вниз]adv:v-u", tokenizer, tagger);

    TestTools.myAssert("низенько-низенько", "низенько-низенько/[низенько-низенько]adv", tokenizer, tagger);
    TestTools.myAssert("такого-сякого", "такого-сякого/[такий-сякий]adj:m:v_rod:&pron:def|такого-сякого/[такий-сякий]adj:m:v_zna:&pron:def|такого-сякого/[такий-сякий]adj:n:v_rod:&pron:def", tokenizer, tagger);
    TestTools.myAssert("великий-превеликий", "великий-превеликий/[великий-превеликий]adj:m:v_naz|великий-превеликий/[великий-превеликий]adj:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("чорній-чорній", "чорній-чорній/[чорний-чорний]adj:f:v_dav|чорній-чорній/[чорний-чорний]adj:f:v_mis|чорній-чорній/[чорніти-чорніти]verb:impr:s:2:imperf", tokenizer, tagger);

    TestTools.myAssert("лікар-гомеопат", "лікар-гомеопат/[лікар-гомеопат]noun:m:v_naz:anim", tokenizer, tagger);
    TestTools.myAssert("лікаря-гомеопата", "лікаря-гомеопата/[лікар-гомеопат]noun:m:v_rod:anim|лікаря-гомеопата/[лікар-гомеопат]noun:m:v_zna:anim", tokenizer, tagger);
    TestTools.myAssert("шмкр-гомеопат", "шмкр-гомеопат/[null]null", tokenizer, tagger);
    TestTools.myAssert("шмкр-ткр", "шмкр-ткр/[null]null", tokenizer, tagger);

    TestTools.myAssert("вчинок-приклад", "вчинок-приклад/[вчинок-приклад]noun:m:v_naz:v-u|вчинок-приклад/[вчинок-приклад]noun:m:v_zna:v-u", tokenizer, tagger);
    TestTools.myAssert("міста-фортеці", "міста-фортеці/[місто-фортеця]noun:n:v_rod|міста-фортеці/[місто-фортеця]noun:p:v_naz|міста-фортеці/[місто-фортеця]noun:p:v_zna", tokenizer, tagger);

    // inanim-anim
    TestTools.myAssert("вчених-новаторів", "вчених-новаторів/[вчений-новатор]noun:p:v_rod:anim:v-u|вчених-новаторів/[вчений-новатор]noun:p:v_zna:anim:v-u", tokenizer, tagger);
    TestTools.myAssert("країна-виробник", "країна-виробник/[країна-виробник]noun:f:v_naz", tokenizer, tagger);
    TestTools.myAssert("банк-виробник", "банк-виробник/[банк-виробник]noun:m:v_naz|банк-виробник/[банк-виробник]noun:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("банки-агенти", "банки-агенти/[банк-агент]noun:p:v_naz|банки-агенти/[банк-агент]noun:p:v_zna|банки-агенти/[банка-агент]noun:p:v_naz|банки-агенти/[банка-агент]noun:p:v_zna", tokenizer, tagger);
    TestTools.myAssert("місто-гігант", "місто-гігант/[місто-гігант]noun:n:v_naz|місто-гігант/[місто-гігант]noun:n:v_zna", tokenizer, tagger);
    TestTools.myAssert("країни-агресори", "країни-агресори/[країна-агресор]noun:p:v_naz|країни-агресори/[країна-агресор]noun:p:v_zna", tokenizer, tagger);
    TestTools.myAssert("поселення-гігант", "поселення-гігант/[поселення-гігант]noun:n:v_naz|поселення-гігант/[поселення-гігант]noun:n:v_zna", tokenizer, tagger);
    
    TestTools.myAssert("сонях-красень", "сонях-красень/[сонях-красень]noun:m:v_naz|сонях-красень/[сонях-красень]noun:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("красень-сонях", "красень-сонях/[красень-сонях]noun:m:v_naz|красень-сонях/[красень-сонях]noun:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("депутатів-привидів", "депутатів-привидів/[депутат-привид]noun:p:v_rod:anim|депутатів-привидів/[депутат-привид]noun:p:v_zna:anim", tokenizer, tagger);
    TestTools.myAssert("дівчата-зірочки", "дівчата-зірочки/[дівча-зірочка]noun:p:v_naz:anim", tokenizer, tagger);

    TestTools.myAssert("абзац-два", "абзац-два/[абзац-два]noun:m:v_naz|абзац-два/[абзац-два]noun:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("сотні-дві", "сотні-дві/[сотня-два]noun:p:v_naz|сотні-дві/[сотня-два]noun:p:v_zna", tokenizer, tagger);
    TestTools.myAssert("тисячею-трьома", "тисячею-трьома/[тисяча-три]noun:f:v_oru|тисячею-трьома/[тисяча-троє]noun:f:v_oru", tokenizer, tagger);

    TestTools.myAssert("одним-двома", "одним-двома/[один-два]numr:m:v_oru|одним-двома/[один-два]numr:n:v_oru|одним-двома/[один-двоє]numr:m:v_oru|одним-двома/[один-двоє]numr:n:v_oru", tokenizer, tagger);
    //TODO: бере іменник п’ята
//    TestTools.myAssert("п'яти-шести", "п'яти-шести/[п'ять-шість]numr:v_dav|п'яти-шести/[п'ять-шість]numr:v_mis|п'яти-шести/[п'ять-шість]numr:v_rod", tokenizer, tagger);
    TestTools.myAssert("п'яти-шести", "п'яти-шести/[п'ята-шість]noun:f:v_rod|п'яти-шести/[п'ять-шість]numr:p:v_dav|п'яти-шести/[п'ять-шість]numr:p:v_mis|п'яти-шести/[п'ять-шість]numr:p:v_rod", tokenizer, tagger);
    TestTools.myAssert("півтори-дві", "півтори-дві/[півтори-два]numr:f:v_naz|півтори-дві/[півтори-два]numr:f:v_zna", tokenizer, tagger);
    TestTools.myAssert("три-чотири", "три-чотири/[три-чотири]numr:p:v_naz|три-чотири/[три-чотири]numr:p:v_zna", tokenizer, tagger);
    TestTools.myAssert("два-чотири", "два-чотири/[два-чотири]numr:m:v_naz|два-чотири/[два-чотири]numr:m:v_zna|два-чотири/[два-чотири]numr:n:v_naz|два-чотири/[два-чотири]numr:n:v_zna", tokenizer, tagger);
    TestTools.myAssert("одному-двох", "одному-двох/[один-два]numr:m:v_mis|одному-двох/[один-два]numr:n:v_mis|одному-двох/[один-двоє]numr:m:v_mis|одному-двох/[один-двоє]numr:n:v_mis", tokenizer, tagger);
    // u2013
    TestTools.myAssert("три–чотири", "три–чотири/[три–чотири]numr:p:v_naz|три–чотири/[три–чотири]numr:p:v_zna", tokenizer, tagger);
    
//    "однією-єдиною"
//    TestTools.myAssert("капуджі-ага", "два-чотири/[два-чотири]numr:v_naz|два-чотири/[два-чотири]numr:v_naz", tokenizer, tagger);
//    TestTools.myAssert("Каладжі-бей", "два-чотири/[два-чотири]numr:v_naz|два-чотири/[два-чотири]numr:v_naz", tokenizer, tagger);
//    TestTools.myAssert("капудан-паша", "два-чотири/[два-чотири]numr:v_naz|два-чотири/[два-чотири]numr:v_naz", tokenizer, tagger);
//    TestTools.myAssert("кальфа-ефенді", "два-чотири/[два-чотири]numr:v_naz|два-чотири/[два-чотири]numr:v_naz", tokenizer, tagger);

    TestTools.myAssert("а-а", "а-а/[а-а]excl", tokenizer, tagger);

    TestTools.myAssert("Москви-ріки", "Москви-ріки/[Москва-ріка]noun:f:v_rod", tokenizer, tagger);
    
    TestTools.myAssert("пів-України", "пів-України/[пів-України]noun:f:v_dav|пів-України/[пів-України]noun:f:v_mis|пів-України/[пів-України]noun:f:v_naz|пів-України/[пів-України]noun:f:v_oru|пів-України/[пів-України]noun:f:v_rod|пів-України/[пів-України]noun:f:v_zna", tokenizer, tagger);

    TestTools.myAssert("кава-еспресо", "кава-еспресо/[кава-еспресо]noun:f:v_naz", tokenizer, tagger);
    TestTools.myAssert("кави-еспресо", "кави-еспресо/[кава-еспресо]noun:f:v_rod", tokenizer, tagger);
    TestTools.myAssert("еспресо-машина", "еспресо-машина/[еспресо-машина]noun:f:v_naz", tokenizer, tagger);
    TestTools.myAssert("програмою-максимум", "програмою-максимум/[програма-максимум]noun:f:v_oru", tokenizer, tagger);

    TestTools.myAssert("Пенсильванія-авеню", "Пенсильванія-авеню/[Пенсильванія-авеню]noun:f:nv", tokenizer, tagger);

    TestTools.myAssert("патолого-анатомічний", "патолого-анатомічний/[патолого-анатомічний]adj:m:v_naz|патолого-анатомічний/[патолого-анатомічний]adj:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("паталого-анатомічний", "паталого-анатомічний/[null]null", tokenizer, tagger);
    //TODO: fix this case (now works like братів-православних)
//    TestTools.myAssert("патолога-анатомічний", "патолога-анатомічний/[null]null", tokenizer, tagger);
    TestTools.myAssert("патолого-гмкнх", "патолого-гмкнх/[null]null", tokenizer, tagger);
    TestTools.myAssert("патолого-голова", "патолого-голова/[null]null", tokenizer, tagger);
    //TODO: remove :compb ?
    TestTools.myAssert("освітньо-культурний", "освітньо-культурний/[освітньо-культурний]adj:m:v_naz:compb|освітньо-культурний/[освітньо-культурний]adj:m:v_zna:compb", tokenizer, tagger);
    TestTools.myAssert("бірмюково-блакитний", "бірмюково-блакитний/[null]null", tokenizer, tagger);
    TestTools.myAssert("сліпуче-яскравого", "сліпуче-яскравого/[сліпуче-яскравий]adj:m:v_rod:compb|сліпуче-яскравого/[сліпуче-яскравий]adj:m:v_zna:compb|сліпуче-яскравого/[сліпуче-яскравий]adj:n:v_rod:compb", tokenizer, tagger);
    TestTools.myAssert("дво-триметровий", "дво-триметровий/[дво-триметровий]adj:m:v_naz|дво-триметровий/[дво-триметровий]adj:m:v_zna", tokenizer, tagger);
    TestTools.myAssert("україно-болгарський", "україно-болгарський/[україно-болгарський]adj:m:v_naz|україно-болгарський/[україно-болгарський]adj:m:v_zna", tokenizer, tagger);

//    TestTools.myAssert("американо-блакитний", "бірмюково-блакитний/[бірмюково-блакитний]adj:m:v_naz|бірмюково-блакитний/[бірмюково-блакитний]adj:m:v_zna", tokenizer, tagger);

    TestTools.myAssert("Дівчинка-першокласниця", "Дівчинка-першокласниця/[дівчинка-першокласниця]noun:f:v_naz:anim", tokenizer, tagger);

    // істота-неістота
    //TODO:
    // про місяця-місяченька
    // бабці-Австрії
    // змагання зі слалому-гіганту
    // голосувати за Тимошенко-прем’єра
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/tokenizers/uk/UkrainianSRXSentenceTokenizerTest.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2005 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */

package org.languagetool.tokenizers.uk;

import junit.framework.TestCase;
import org.languagetool.TestTools;
import org.languagetool.language.Ukrainian;
import org.languagetool.tokenizers.SRXSentenceTokenizer;

public class UkrainianSRXSentenceTokenizerTest extends TestCase {

  private final SRXSentenceTokenizer stokenizer = new SRXSentenceTokenizer(new Ukrainian());

  public final void testTokenize() {
    testSplit("Це просте речення.");
    testSplit("Вони приїхали в Париж. ", "Але там їм геть не сподобалося.");
    testSplit("Панк-рок — напрям у рок-музиці, що виник у середині 1970-х рр. у США і Великобританії.");
    testSplit("Разом із втечами, вже у XV ст. почастішали збройні виступи селян.");
    testSplit("На початок 1994 р. державний борг України становив 4,8 млрд. дол.");
    testSplit("Київ, вул. Сагайдачного, буд. 43, кв. 4.");
    testSplit("Наша зустріч з А. Марчуком і Г. В. Тріскою відбулася в грудні минулого року.");
    testSplit("Наша зустріч з А.Марчуком і М.В.Хвилею відбулася в грудні минулого року.");
    testSplit("Комендант преподобний С.\u00A0Мокітімі");
    testSplit("Комендант преподобний С.\u00A0С.\u00A0Мокітімі 1.");
    testSplit("Комендант преподобний С.\u00A0С. Мокітімі 2.");
    testSplit("Склад: акад. Вернадський, проф. Харченко, доц. Семеняк.");
    testSplit("Опергрупа приїхала в с. Лісове.");
    testSplit("300 р. до н. е.");
    testSplit("Пролісок (рос. пролесок) — маленька квітка.");
    testSplit("Квітка Цісик (англ. Kvitka Cisyk також Kacey Cisyk від ініціалів К.С.); 4 квітня 1953р., Квінз, Нью-Йорк — 29 березня 1998 р., Мангеттен, Нью-Йорк) — американська співачка українського походження.");
    testSplit("До Інституту ім. Глієра під'їжджає чорне авто."); 
    testSplit("До табору «Артек».");
  }

  private void testSplit(final String... sentences) {
    TestTools.testSplit(sentences, stokenizer);
  }

}


File: languagetool-language-modules/uk/src/test/java/org/languagetool/tokenizers/uk/UkrainianWordTokenizerTest.java
/* LanguageTool, a natural language style checker 
 * Copyright (C) 2005 Daniel Naber (http://www.danielnaber.de)
 * 
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
 * USA
 */

package org.languagetool.tokenizers.uk;

import java.util.Arrays;
import java.util.List;

import junit.framework.TestCase;

public class UkrainianWordTokenizerTest extends TestCase {
  private final UkrainianWordTokenizer w = new UkrainianWordTokenizer();

  public void testTokenize() {
    List<String> testList = w.tokenize("Вони прийшли додому.");
    assertEquals(Arrays.asList("Вони", " ", "прийшли", " ", "додому", "."), testList);

    testList = w.tokenize("Вони прийшли пʼятими зів’ялими.");
    assertEquals(Arrays.asList("Вони", " ", "прийшли", " ", "п'ятими", " ", "зів'ялими", "."), testList);

//    testList = w.tokenize("Вони\u0301 при\u00ADйшли пʼя\u0301тими зів’я\u00ADлими.");
//    assertEquals(Arrays.asList("Вони", " ", "прийшли", " ", "п'ятими", " ", "зів'ялими", "."), testList);

    testList = w.tokenize("Засідав І.Єрмолюк.");
    assertEquals(Arrays.asList("Засідав", " ", "І", ".", "Єрмолюк", "."), testList);

    testList = w.tokenize("Засідав І.П.Єрмолюк.");
    assertEquals(Arrays.asList("Засідав", " ", "І", ".", "П", ".", "Єрмолюк", "."), testList);

    testList = w.tokenize("І.\u00A0Єрмолюк.");
    assertEquals(Arrays.asList("І", ".", "\u00A0", "Єрмолюк", "."), testList);

    testList = w.tokenize("300 грн. на балансі");
    assertEquals(Arrays.asList("300", " ", "грн.", " ", "на", " ", "балансі"), testList);

    testList = w.tokenize("надійшло 2,2 мільйона");
    assertEquals(Arrays.asList("надійшло", " ", "2,2", " ", "мільйона"), testList);

    testList = w.tokenize("надійшло 84,46 мільйона");
    assertEquals(Arrays.asList("надійшло", " ", "84,46", " ", "мільйона"), testList);

//    testList = w.tokenize("надійшло 2 000 тон");
//    assertEquals(Arrays.asList("надійшло", " ", "2 000", " ", "тон"), testList);

    testList = w.tokenize("сталося 14.07.2001 вночі");
    assertEquals(Arrays.asList("сталося", " ", "14.07.2001", " ", "вночі"), testList);

    testList = w.tokenize("вчора о 7.30 ранку");
    assertEquals(Arrays.asList("вчора", " ", "о", " ", "7.30", " ", "ранку"), testList);

    testList = w.tokenize("я українець(сміється");
    assertEquals(Arrays.asList("я", " ", "українець", "(", "сміється"), testList);
        
    testList = w.tokenize("ОУН(б) та КП(б)У");
    assertEquals(Arrays.asList("ОУН(б)", " ", "та", " ", "КП(б)У"), testList);

    testList = w.tokenize("Негода є... заступником");
    assertEquals(Arrays.asList("Негода", " ", "є", "...", " ", "заступником"), testList);

    testList = w.tokenize("140 тис. працівників");
    assertEquals(Arrays.asList("140", " ", "тис.", " ", "працівників"), testList);

    testList = w.tokenize("проф. Артюхов");
    assertEquals(Arrays.asList("проф.", " ", "Артюхов"), testList);
  }

}
