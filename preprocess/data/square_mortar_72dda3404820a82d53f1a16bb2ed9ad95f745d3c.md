Refactoring Types: ['Move Method']
a/mortar/dagger1support/ObjectGraphService.java
package mortar.dagger1support;

import android.app.Activity;
import android.content.Context;
import dagger.ObjectGraph;
import java.util.Collection;
import mortar.MortarScope;
import mortar.bundler.BundleServiceRunner;

import static mortar.MortarScope.getScope;

/**
 * Provides utility methods for using Mortar with Dagger 1.
 */
public class ObjectGraphService {
  public static final String SERVICE_NAME = ObjectGraphService.class.getName();

  /**
   * Create a new {@link ObjectGraph} based on the given module. The new graph will extend
   * the graph found in the parent scope (via {@link ObjectGraph#plus}), if there is one.
   */
  public static ObjectGraph create(MortarScope parent, Object... daggerModules) {
    ObjectGraph parentGraph = getObjectGraph(parent);

    return parentGraph == null ? ObjectGraph.create(daggerModules)
        : parentGraph.plus(daggerModules);
  }

  public static ObjectGraph getObjectGraph(Context context) {
    return (ObjectGraph) getScope(context).getService(ObjectGraphService.SERVICE_NAME);
  }

  public static ObjectGraph getObjectGraph(MortarScope scope) {
    return scope.getService(ObjectGraphService.SERVICE_NAME);
  }

  /**
   * A convenience wrapper for {@link ObjectGraphService#getObjectGraph} to simplify dynamic
   * injection, typically for {@link Activity} and {@link android.view.View} instances that must be
   * instantiated by Android.
   */
  public static void inject(Context context, Object object) {
    getObjectGraph(context).inject(object);
  }

  /**
   * A convenience wrapper for {@link ObjectGraphService#getObjectGraph} to simplify dynamic
   * injection, typically for {@link Activity} and {@link android.view.View} instances that must be
   * instantiated by Android.
   */
  public static void inject(MortarScope scope, Object object) {
    getObjectGraph(scope).inject(object);
  }

  private static ObjectGraph createSubgraphBlueprintStyle(ObjectGraph parentGraph,
      Object daggerModule) {
    ObjectGraph newGraph;
    if (daggerModule == null) {
      newGraph = parentGraph.plus();
    } else if (daggerModule instanceof Collection) {
      Collection c = (Collection) daggerModule;
      newGraph = parentGraph.plus(c.toArray(new Object[c.size()]));
    } else {
      newGraph = parentGraph.plus(daggerModule);
    }
    return newGraph;
  }

  /**
   * Returns the existing {@link MortarScope} scope for the given {@link Activity}, or
   * uses the {@link Blueprint} to create one if none is found. The scope will provide
   * {@link mortar.bundler.BundleService} and {@link BundleServiceRunner}.
   * <p/>
   * It is expected that this method will be called from {@link Activity#onCreate}. Calling
   * it at other times may lead to surprises.
   *
   * @see MortarScope.Builder#withService(String, Object)
   * @deprecated This method is provided to ease migration from earlier releases, which
   * coupled Dagger and Activity integration. Instead build new scopes with {@link
   * MortarScope#buildChild()}, and bind {@link ObjectGraphService} and
   * {@link BundleServiceRunner} instances to them.
   */
  @Deprecated public static MortarScope requireActivityScope(MortarScope parentScope,
      Blueprint blueprint) {
    String childName = blueprint.getMortarScopeName();
    MortarScope child = parentScope.findChild(childName);
    if (child == null) {
      ObjectGraph parentGraph = parentScope.getService(ObjectGraphService.SERVICE_NAME);
      Object daggerModule = blueprint.getDaggerModule();
      Object childGraph = createSubgraphBlueprintStyle(parentGraph, daggerModule);
      child = parentScope.buildChild()
          .withService(ObjectGraphService.SERVICE_NAME, childGraph)
          .withService(BundleServiceRunner.SERVICE_NAME, new BundleServiceRunner())
          .build(childName);
    }
    return child;
  }

  /**
   * Returns the existing child whose name matches the given {@link Blueprint}'s
   * {@link Blueprint#getMortarScopeName()} value. If there is none, a new child is created
   * based on {@link Blueprint#getDaggerModule()}. Note that
   * {@link Blueprint#getDaggerModule()} is not called otherwise.
   *
   * @throws IllegalStateException if this scope has been destroyed
   * @see MortarScope.Builder#withService(String, Object)
   * @deprecated This method is provided to ease migration from earlier releases, which
   * required Dagger integration. Instead build new scopes with {@link
   * MortarScope#buildChild()}, and bind {@link ObjectGraphService}  instances to them.
   */
  @Deprecated public static MortarScope requireChild(MortarScope parentScope, Blueprint blueprint) {
    String childName = blueprint.getMortarScopeName();
    MortarScope child = parentScope.findChild(childName);
    if (child == null) {
      ObjectGraph parentGraph = parentScope.getService(ObjectGraphService.SERVICE_NAME);
      Object daggerModule = blueprint.getDaggerModule();
      Object childGraph = createSubgraphBlueprintStyle(parentGraph, daggerModule);
      child = parentScope.buildChild()
          .withService(ObjectGraphService.SERVICE_NAME, childGraph)
          .build(childName);
    }
    return child;
  }
}


File: mortar-dagger1/src/test/java/mortar/ObjectGraphServiceTest.java
/*
 * Copyright 2013 Square Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package mortar;

import android.content.Context;
import dagger.Module;
import dagger.ObjectGraph;
import dagger.Provides;
import java.lang.annotation.Retention;
import java.util.concurrent.atomic.AtomicInteger;
import javax.inject.Inject;
import javax.inject.Qualifier;
import mortar.dagger1support.Blueprint;
import mortar.dagger1support.ObjectGraphService;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import static dagger.ObjectGraph.create;
import static java.lang.annotation.RetentionPolicy.RUNTIME;
import static java.util.Arrays.asList;
import static mortar.dagger1support.ObjectGraphService.getObjectGraph;
import static mortar.dagger1support.ObjectGraphService.requireChild;
import static org.fest.assertions.api.Assertions.assertThat;
import static org.fest.assertions.api.Assertions.fail;
import static org.mockito.Matchers.any;
import static org.mockito.Matchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.MockitoAnnotations.initMocks;

@SuppressWarnings("InnerClassMayBeStatic") public class ObjectGraphServiceTest {

  @Mock Context context;
  @Mock Scoped scoped;

  @Qualifier @Retention(RUNTIME) @interface Apple {
  }

  @Qualifier @Retention(RUNTIME) @interface Bagel {
  }

  @Qualifier @Retention(RUNTIME) @interface Carrot {
  }

  @Qualifier @Retention(RUNTIME) @interface Dogfood {
  }

  @Qualifier @Retention(RUNTIME) @interface Eggplant {
  }

  @Module(injects = HasApple.class) class Able {
    @Provides @Apple String provideApple() {
      return Apple.class.getName();
    }
  }

  class AbleBlueprint implements Blueprint {
    @Override public String getMortarScopeName() {
      return Apple.class.getName();
    }

    @Override public Object getDaggerModule() {
      return new Able();
    }
  }

  @Module(injects = HasBagel.class) class Baker {
    @Provides @Bagel String provideBagel() {
      return Bagel.class.getName();
    }
  }

  class BakerBlueprint implements Blueprint {
    @Override public String getMortarScopeName() {
      return Bagel.class.getName();
    }

    @Override public Object getDaggerModule() {
      return new Baker();
    }
  }

  @Module(injects = HasCarrot.class) class Charlie {
    @Provides @Carrot String provideCharlie() {
      return Carrot.class.getName();
    }
  }

  class CharlieBlueprint implements Blueprint {
    @Override public String getMortarScopeName() {
      return Carrot.class.getName();
    }

    @Override public Object getDaggerModule() {
      return new Charlie();
    }
  }

  @Module(injects = HasDogfood.class) class Delta {
    @Provides @Dogfood String provideDogfood() {
      return Dogfood.class.getName();
    }
  }

  class DeltaBlueprint implements Blueprint {
    @Override public String getMortarScopeName() {
      return Dogfood.class.getName();
    }

    @Override public Object getDaggerModule() {
      return new Delta();
    }
  }

  @Module(injects = HasEggplant.class) class Echo {
    @Provides @Eggplant String provideEggplant() {
      return Eggplant.class.getName();
    }
  }

  class MoreModules implements Blueprint {

    @Override public String getMortarScopeName() {
      return "Moar";
    }

    @Override public Object getDaggerModule() {
      return asList(new Delta(), new Echo());
    }
  }

  class NoModules implements Blueprint {

    @Override public String getMortarScopeName() {
      return "Nothing";
    }

    @Override public Object getDaggerModule() {
      return null;
    }
  }

  static class HasApple {
    @Inject @Apple String string;
  }

  static class HasBagel {
    @Inject @Bagel String string;
  }

  static class HasCarrot {
    @Inject @Carrot String string;
  }

  static class HasDogfood {
    @Inject @Dogfood String string;
  }

  static class HasEggplant {
    @Inject @Eggplant String string;
  }

  @Before public void setUp() {
    initMocks(this);
  }

  @Test public void createMortarScopeUsesModules() {
    MortarScope scope = createRootScope(create(new Able(), new Baker()));
    ObjectGraph objectGraph = getObjectGraph(scope);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    try {
      objectGraph.get(HasCarrot.class);
    } catch (IllegalArgumentException e) {
      // pass
      return;
    }
    fail("Expected IllegalArgumentException");
  }

  @Test public void destroyRoot() {
    MortarScope scope = createRootScope(create(new Able()));
    scope.register(scoped);
    scope.destroy();
    verify(scoped).onExitScope();
  }

  @Test public void activityScopeName() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());

    String bagel = Bagel.class.getName();
    assertThat(activityScope.getName()).isEqualTo(bagel);
    assertThat(root.findChild(bagel)).isSameAs(activityScope);
    assertThat(requireChild(root, new BakerBlueprint())).isSameAs(activityScope);
    assertThat(ObjectGraphService.requireActivityScope(root, new BakerBlueprint())).isSameAs(
        activityScope);
    assertThat(root.findChild("herman")).isNull();
  }

  @Test public void getActivityScopeWithOneModule() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    ObjectGraph objectGraph = getObjectGraph(activityScope);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    try {
      objectGraph.get(HasCarrot.class);
    } catch (IllegalArgumentException e) {
      // pass
      return;
    }
    fail("Expected IllegalArgumentException");
  }

  @Test public void getActivityScopeWithMoreModules() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new MoreModules());
    ObjectGraph objectGraph = getObjectGraph(activityScope);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasDogfood.class).string).isEqualTo(Dogfood.class.getName());
    assertThat(objectGraph.get(HasEggplant.class).string).isEqualTo(Eggplant.class.getName());
    try {
      objectGraph.get(HasCarrot.class);
    } catch (IllegalArgumentException e) {
      // pass
      return;
    }
    fail("Expected IllegalArgumentException");
  }

  @Test public void destroyActivityScopeDirect() {
    MortarScope root = createRootScope(create(new Able()));
    BakerBlueprint blueprint = new BakerBlueprint();
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, blueprint);
    assertThat(root.findChild(blueprint.getMortarScopeName())).isSameAs(activityScope);
    activityScope.register(scoped);
    activityScope.destroy();
    verify(scoped).onExitScope();
    assertThat(root.findChild(blueprint.getMortarScopeName())).isNull();
  }

  @Test public void destroyActivityScopeRecursive() {
    MortarScope root = createRootScope(create(new Able()));
    BakerBlueprint blueprint = new BakerBlueprint();
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, blueprint);
    assertThat(root.findChild(blueprint.getMortarScopeName())).isSameAs(activityScope);
    activityScope.register(scoped);
    root.destroy();
    verify(scoped).onExitScope();

    IllegalStateException caught = null;
    try {
      getObjectGraph(activityScope);
    } catch (IllegalStateException e) {
      caught = e;
    }
    assertThat(caught).isNotNull();
  }

  @Test public void activityChildScopeName() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new CharlieBlueprint());

    String carrot = Carrot.class.getName();
    assertThat(child.getName()).isEqualTo(carrot);
    assertThat(activityScope.findChild(carrot)).isSameAs(child);
    assertThat(requireChild(activityScope, new CharlieBlueprint())).isSameAs(child);
    assertThat(activityScope.findChild("herman")).isNull();
  }

  @Test public void requireGrandchildWithOneModule() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new CharlieBlueprint());
    MortarScope grandchild = requireChild(child, new DeltaBlueprint());
    ObjectGraph objectGraph = getObjectGraph(grandchild);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    assertThat(objectGraph.get(HasCarrot.class).string).isEqualTo(Carrot.class.getName());
    assertThat(objectGraph.get(HasDogfood.class).string).isEqualTo(Dogfood.class.getName());
    try {
      objectGraph.get(HasEggplant.class);
    } catch (IllegalArgumentException e) {
      // pass
      return;
    }
    fail("Expected IllegalArgumentException");
  }

  @Test public void requireGrandchildWithMoreModules() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new CharlieBlueprint());
    MortarScope grandchild = requireChild(child, new MoreModules());

    ObjectGraph objectGraph = getObjectGraph(grandchild);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    assertThat(objectGraph.get(HasCarrot.class).string).isEqualTo(Carrot.class.getName());
    assertThat(objectGraph.get(HasDogfood.class).string).isEqualTo(Dogfood.class.getName());
    assertThat(objectGraph.get(HasEggplant.class).string).isEqualTo(Eggplant.class.getName());
    try {
      objectGraph.get(String.class);
    } catch (IllegalArgumentException e) {
      // pass
      return;
    }
    fail("Expected IllegalArgumentException");
  }

  @Test public void requireGrandchildWithNoModules() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new CharlieBlueprint());
    MortarScope grandchild = requireChild(child, new NoModules());

    ObjectGraph objectGraph = getObjectGraph(grandchild);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    assertThat(objectGraph.get(HasCarrot.class).string).isEqualTo(Carrot.class.getName());

    try {
      objectGraph.get(String.class);
    } catch (IllegalArgumentException e) {
      // pass
      return;
    }
    fail("Expected IllegalArgumentException");
  }

  @Test public void destroyActivityChildScopeDirect() {
    MortarScope root = createRootScope(create(new Able()));
    CharlieBlueprint blueprint = new CharlieBlueprint();
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, blueprint);
    assertThat(activityScope.findChild(blueprint.getMortarScopeName())).isSameAs(child);
    child.register(scoped);
    child.destroy();
    verify(scoped).onExitScope();
    assertThat(activityScope.findChild(blueprint.getMortarScopeName())).isNull();
  }

  @Test public void destroyActivityChildScopeRecursive() {
    MortarScope root = createRootScope(create(new Able()));
    CharlieBlueprint blueprint = new CharlieBlueprint();
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, blueprint);
    assertThat(activityScope.findChild(blueprint.getMortarScopeName())).isSameAs(child);
    child.register(scoped);
    root.destroy();
    verify(scoped).onExitScope();

    IllegalStateException caught = null;
    try {
      assertThat(getObjectGraph(child)).isNull();
    } catch (IllegalStateException e) {
      caught = e;
    }
    assertThat(caught).isNotNull();
  }

  @Test public void activityGrandchildScopeName() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new CharlieBlueprint());
    MortarScope grandchild = requireChild(child, new DeltaBlueprint());

    String dogfood = Dogfood.class.getName();
    assertThat(grandchild.getName()).isEqualTo(dogfood);
    assertThat(child.findChild(dogfood)).isSameAs(grandchild);
    assertThat(requireChild(child, new DeltaBlueprint())).isSameAs(grandchild);
    assertThat(child.findChild("herman")).isNull();
  }

  @Test public void requireChildWithOneModule() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new CharlieBlueprint());

    ObjectGraph objectGraph = getObjectGraph(child);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    assertThat(objectGraph.get(HasCarrot.class).string).isEqualTo(Carrot.class.getName());
  }

  @Test public void requireChildWithMoreModules() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope activityScope = ObjectGraphService.requireActivityScope(root, new BakerBlueprint());
    MortarScope child = requireChild(activityScope, new MoreModules());

    ObjectGraph objectGraph = getObjectGraph(child);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
    assertThat(objectGraph.get(HasBagel.class).string).isEqualTo(Bagel.class.getName());
    assertThat(objectGraph.get(HasDogfood.class).string).isEqualTo(Dogfood.class.getName());
    assertThat(objectGraph.get(HasEggplant.class).string).isEqualTo(Eggplant.class.getName());
  }

  @Test public void requireChildWithNoModules() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope child = requireChild(root, new NoModules());

    ObjectGraph objectGraph = getObjectGraph(child);
    assertThat(objectGraph.get(HasApple.class).string).isEqualTo(Apple.class.getName());
  }

  @Test public void handlesRecursiveDestroy() {
    final AtomicInteger i = new AtomicInteger(0);

    final MortarScope scope = createRootScope(create(new Able()));
    scope.register(new Scoped() {
      @Override public void onEnterScope(MortarScope scope) {
      }

      @Override public void onExitScope() {
        i.incrementAndGet();
        scope.destroy();
      }
    });
    scope.destroy();
    assertThat(i.get()).isEqualTo(1);
  }

  @Test public void inject() {
    final MortarScope root = createRootScope(create(new Able()));
    when(context.getSystemService(any(String.class))).then(new Answer<Object>() {
      @Override public Object answer(InvocationOnMock invocation) throws Throwable {
        return root.getService((String) invocation.getArguments()[0]);
      }
    });
    HasApple apple = new HasApple();
    ObjectGraphService.inject(context, apple);
    assertThat(apple.string).isEqualTo(Apple.class.getName());
  }

  @Test public void getScope() {
    MortarScope root = createRootScope(create(new Able()));
    when(context.getSystemService(MortarScope.MORTAR_SERVICE)).thenReturn(root);
    assertThat(MortarScope.getScope(context)).isSameAs(root);
  }

  @Test public void canGetNameFromDestroyed() {
    MortarScope scope = createRootScope(create(new Able()));
    String name = scope.getName();
    assertThat(name).isNotNull();
    scope.destroy();
    assertThat(scope.getName()).isEqualTo(name);
  }

  @Test public void cannotGetObjectGraphFromDestroyed() {
    MortarScope scope = createRootScope(create(new Able()));
    scope.destroy();

    IllegalStateException caught = null;
    try {
      getObjectGraph(scope);
    } catch (IllegalStateException e) {
      caught = e;
    }
    assertThat(caught).isNotNull();
  }

  @Test public void cannotGetObjectGraphFromContextOfDestroyed() {
    MortarScope scope = createRootScope(create(new Able()));
    Context context = mockContext(scope);
    scope.destroy();

    IllegalStateException caught = null;
    try {
      getObjectGraph(context);
    } catch (IllegalStateException e) {
      caught = e;
    }
    assertThat(caught).isNotNull();
  }

  @Test(expected = IllegalStateException.class) public void cannotRegisterOnDestroyed() {
    MortarScope scope = createRootScope(create(new Able()));
    scope.destroy();
    scope.register(scoped);
  }

  @Test(expected = IllegalStateException.class) public void cannotFindChildFromDestroyed() {
    MortarScope scope = createRootScope(create(new Able()));
    scope.destroy();
    scope.findChild("foo");
  }

  @Test(expected = IllegalStateException.class) public void cannotRequireChildFromDestroyed() {
    MortarScope scope = createRootScope(create(new Able()));
    scope.destroy();
    requireChild(scope, new AbleBlueprint());
  }

  @Test public void destroyIsIdempotent() {
    MortarScope root = createRootScope(create(new Able()));
    MortarScope child = requireChild(root, new NoModules());

    final AtomicInteger destroys = new AtomicInteger(0);
    child.register(new Scoped() {
      @Override public void onEnterScope(MortarScope scope) {
      }

      @Override public void onExitScope() {
        destroys.addAndGet(1);
      }
    });

    child.destroy();
    assertThat(destroys.get()).isEqualTo(1);

    child.destroy();
    assertThat(destroys.get()).isEqualTo(1);
  }

  @Test public void rootDestroyIsIdempotent() {
    MortarScope scope = createRootScope(create(new Able()));

    final AtomicInteger destroys = new AtomicInteger(0);
    scope.register(new Scoped() {
      @Override public void onEnterScope(MortarScope scope) {
      }

      @Override public void onExitScope() {
        destroys.addAndGet(1);
      }
    });

    scope.destroy();
    assertThat(destroys.get()).isEqualTo(1);

    scope.destroy();
    assertThat(destroys.get()).isEqualTo(1);
  }

  @Test public void isDestroyedStartsFalse() {
    MortarScope root = createRootScope(create(new Able()));
    assertThat(root.isDestroyed()).isFalse();
  }

  @Test public void isDestroyedGetsSet() {
    MortarScope root = createRootScope(create(new Able()));
    root.destroy();
    assertThat(root.isDestroyed()).isTrue();
  }

  private static MortarScope createRootScope(ObjectGraph objectGraph) {
    return MortarScope.buildRootScope()
        .withService(ObjectGraphService.SERVICE_NAME, objectGraph)
        .build("Root");
  }


  private static Context mockContext(MortarScope root) {
    final MortarScope scope = root;
    Context appContext = mock(Context.class);
    when(appContext.getSystemService(anyString())).thenAnswer(new Answer<Object>() {
      @Override public Object answer(InvocationOnMock invocation) throws Throwable {
        String name = (String) invocation.getArguments()[0];
        return scope.hasService(name) ? scope.getService(name) : null;
      }
    });
    return appContext;
  }
}


File: mortar/src/main/java/mortar/bundler/BundleServiceRunner.java
package mortar.bundler;

import android.content.Context;
import android.os.Bundle;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.NavigableSet;
import java.util.TreeSet;
import mortar.MortarScope;
import mortar.Presenter;
import mortar.Scoped;

public class BundleServiceRunner implements Scoped {
  public static final String SERVICE_NAME = BundleServiceRunner.class.getName();

  public static BundleServiceRunner getBundleServiceRunner(Context context) {
    return (BundleServiceRunner) context.getSystemService(SERVICE_NAME);
  }

  public static BundleServiceRunner getBundleServiceRunner(MortarScope scope) {
    return scope.getService(SERVICE_NAME);
  }

  final Map<String, BundleService> scopedServices = new LinkedHashMap<>();
  final NavigableSet<BundleService> servicesToBeLoaded =
      new TreeSet<>(new BundleServiceComparator());

  Bundle rootBundle;

  enum State {
    IDLE, LOADING, SAVING
  }

  State state = State.IDLE;

  private String rootScopePath;

  BundleService requireBundleService(MortarScope scope) {
    BundleService service = scopedServices.get(bundleKey(scope));
    if (service == null) {
      service = new BundleService(this, scope);
      service.init();
    }
    return service;
  }

  @Override public void onEnterScope(MortarScope scope) {
    if (rootScopePath != null) throw new IllegalStateException("Cannot double register");
    rootScopePath = scope.getPath();
  }

  @Override public void onExitScope() {
    // Nothing to do.
  }

  /**
   * To be called from the host {@link android.app.Activity}'s {@link
   * android.app.Activity#onCreate}. Calls the registered {@link Bundler}'s {@link Bundler#onLoad}
   * methods. To avoid redundant calls to {@link Presenter#onLoad} it's best to call this before
   * {@link android.app.Activity#setContentView}.
   */
  public void onCreate(Bundle savedInstanceState) {
    rootBundle = savedInstanceState;

    for (Map.Entry<String, BundleService> entry : scopedServices.entrySet()) {
      BundleService scopedService = entry.getValue();
      if (scopedService.updateScopedBundleOnCreate(rootBundle)) {
        servicesToBeLoaded.add(scopedService);
      }
    }
    finishLoading();
  }

  /**
   * To be called from the host {@link android.app.Activity}'s {@link
   * android.app.Activity#onSaveInstanceState}. Calls the registrants' {@link Bundler#onSave}
   * methods.
   */
  public void onSaveInstanceState(Bundle outState) {
    if (state != State.IDLE) {
      throw new IllegalStateException("Cannot handle onSaveInstanceState while " + state);
    }
    rootBundle = outState;

    state = State.SAVING;

    // Make a dwindling copy of the services, in case one is deleted as a side effect
    // of another's onSave.
    List<Map.Entry<String, BundleService>> servicesToBeSaved =
        new ArrayList<>(scopedServices.entrySet());

    while (!servicesToBeSaved.isEmpty()) {
      Map.Entry<String, BundleService> entry = servicesToBeSaved.remove(0);
      if (scopedServices.containsKey(entry.getKey())) entry.getValue().saveToRootBundle(rootBundle);
    }

    state = State.IDLE;
  }

  void finishLoading() {
    if (state != State.IDLE) throw new AssertionError("Unexpected state " + state);
    state = State.LOADING;

    while (!servicesToBeLoaded.isEmpty()) {
      BundleService next = servicesToBeLoaded.first();
      next.loadOne();
      if (!next.needsLoading()) servicesToBeLoaded.remove(next);
    }

    state = State.IDLE;
  }

  String bundleKey(MortarScope scope) {
    if (rootScopePath == null) throw new IllegalStateException("Was this service not registered?");
    String path = scope.getPath();
    if (!path.startsWith(rootScopePath)) {
      throw new IllegalArgumentException(String.format("\"%s\" is not under \"%s\"", scope,
          rootScopePath));
    }

    return path.substring(rootScopePath.length());
  }
}


File: mortar/src/test/java/mortar/MortarScopeTest.java
package mortar;

import android.content.Context;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.Before;
import org.junit.Test;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;

import static mortar.MortarScope.DIVIDER;
import static org.fest.assertions.api.Assertions.assertThat;
import static org.junit.Assert.fail;
import static org.mockito.Matchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

public class MortarScopeTest {
  MortarScope.Builder scopeBuilder;

  @Before public void setUp() {
    scopeBuilder = MortarScope.buildRootScope();
  }

  @Test public void illegalScopeName() {
    try {
      scopeBuilder.build("Root" + DIVIDER);
      fail();
    } catch (IllegalArgumentException e) {
      assertThat(e).hasMessageContaining("must not contain");
    }
  }

  @Test public void noServiceRebound() {
    scopeBuilder.withService("ServiceName", new Object());
    try {
      scopeBuilder.withService("ServiceName", new Object());
      fail();
    } catch (IllegalArgumentException e) {
      assertThat(e).hasMessageContaining("cannot be rebound");
    }
  }

  @Test public void nullServiceBound() {
    try {
      scopeBuilder.withService("ServiceName", null);
      fail();
    } catch (NullPointerException e) {
      assertThat(e).hasMessage("service == null");
    }
  }

  @Test public void buildScopeWithChild() {
    MortarScope rootScope = scopeBuilder.build("Root");
    MortarScope childScope = rootScope.buildChild().build("Child");
    assertThat(rootScope.children.size()).isEqualTo(1);
    assertThat(childScope.parent).isEqualTo(rootScope);
    assertThat(childScope.getPath()).isEqualTo("Root" + DIVIDER + "Child");
  }

  @Test public void findParentServiceFromChildScope() {
    Object dummyService = new Object();
    MortarScope rootScope = scopeBuilder.withService("ServiceOne", dummyService).build("Root");
    MortarScope childScope = rootScope.buildChild().build("Child");
    assertThat(childScope.getService("ServiceOne")).isEqualTo(dummyService);
  }

  @Test public void noChildrenWithSameName() {
    MortarScope rootScope = scopeBuilder.build("Root");
    rootScope.buildChild().build("childOne");
    try {
      rootScope.buildChild().build("childOne");
      fail();
    } catch (IllegalArgumentException e) {
      assertThat(e).hasMessageContaining("already has a child named");
    }
  }

  @Test public void throwIfNoServiceFoundForGivenName() {
    Object dummyService = new Object();
    MortarScope rootScope = scopeBuilder.withService("ServiceOne", dummyService).build("Root");
    assertThat(rootScope.getService("ServiceOne")).isNotNull();
    try {
      rootScope.getService("SearchThis");
      fail();
    } catch (IllegalArgumentException e) {
      assertThat(e).hasMessage("No service found named \"SearchThis\"");
    }
  }

  @Test public void throwIfFindChildAfterDestroyed() {
    MortarScope rootScope = scopeBuilder.build("Root");
    MortarScope childScope = rootScope.buildChild().build("ChildOne");

    assertThat(rootScope.findChild("ChildOne")).isNotNull().isEqualTo(childScope);

    rootScope.destroy();
    assertThat(childScope.isDestroyed()).isTrue();
    assertThat(rootScope.isDestroyed()).isTrue();

    try {
      rootScope.findChild("ChildOne");
      fail();
    } catch (IllegalStateException e) {
      assertThat(e).hasMessageContaining("destroyed");
    }
  }

  @Test public void throwIfFindServiceAfterDestroyed() {
    Object dummyService = new Object();
    MortarScope rootScope = scopeBuilder.withService("ServiceOne", dummyService).build("Root");
    assertThat(rootScope.getService("ServiceOne")).isEqualTo(dummyService);

    rootScope.destroy();
    assertThat(rootScope.isDestroyed()).isTrue();

    try {
      rootScope.getService("ServiceOne");
      fail();
    } catch (IllegalStateException e) {
      assertThat(e).hasMessageContaining("destroyed");
    }
  }

  @Test public void tearDownChildrenBeforeParent() {
    MortarScope rootScope = scopeBuilder.build("Root");
    MortarScope childScope = rootScope.buildChild().build("ChildOne");
    final AtomicBoolean childDestroyed = new AtomicBoolean(false);
    childScope.register(new Scoped() {
      @Override public void onEnterScope(MortarScope scope) {
      }

      @Override public void onExitScope() {
        childDestroyed.set(true);
      }
    });
    rootScope.register(new Scoped() {
      @Override public void onEnterScope(MortarScope scope) {
      }

      @Override public void onExitScope() {
        assertThat(childDestroyed.get()).isTrue();
      }
    });
    rootScope.destroy();
  }

  @Test public void getScope() {
    MortarScope root = scopeBuilder.build("root");
    Context context = mockContext(root);
    assertThat(MortarScope.getScope(context)).isSameAs(root);
  }

  @Test public void getScopeReturnsDeadScope() {
    MortarScope root = scopeBuilder.build("root");
    Context context = mockContext(root);
    root.destroy();
    assertThat(MortarScope.getScope(context)).isSameAs(root);
  }

  private Context mockContext(MortarScope root) {
    final MortarScope scope = root;
    Context appContext = mock(Context.class);
    when(appContext.getSystemService(anyString())).thenAnswer(new Answer<Object>() {
      @Override public Object answer(InvocationOnMock invocation) throws Throwable {
        String name = (String) invocation.getArguments()[0];
        return scope.hasService(name) ? scope.getService(name) : null;
      }
    });
    return appContext;
  }
}
