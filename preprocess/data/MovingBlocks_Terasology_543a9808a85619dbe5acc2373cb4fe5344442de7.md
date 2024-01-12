Refactoring Types: ['Move Class', 'Move Attribute', 'Inline Method', 'Move Method']
MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.editor;

import com.google.common.collect.Lists;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.editor.properties.SceneProperties;
import org.terasology.editor.ui.MainWindow;
import org.terasology.engine.GameEngine;
import org.terasology.engine.TerasologyEngine;
import org.terasology.engine.modes.StateMainMenu;
import org.terasology.engine.paths.PathManager;
import org.terasology.engine.subsystem.EngineSubsystem;
import org.terasology.engine.subsystem.lwjgl.LwjglAudio;
import org.terasology.engine.subsystem.lwjgl.LwjglCustomViewPort;
import org.terasology.engine.subsystem.lwjgl.LwjglGraphics;
import org.terasology.engine.subsystem.lwjgl.LwjglInput;
import org.terasology.engine.subsystem.lwjgl.LwjglTimer;

import javax.swing.*;
import java.util.Collection;

/**
 * TeraEd main class.
 *
 * @author Benjamin Glatzel
 */
@SuppressWarnings("serial")
public final class TeraEd extends JWindow {

    private MainWindow mainWindow;
    private TerasologyEngine engine;
    private final Logger logger = LoggerFactory.getLogger(TeraEd.class);

    private SceneProperties sceneProperties;

    public static void main(String[] args) {
        new TeraEd().run();
    }

    public void run() {
        JPopupMenu.setDefaultLightWeightPopupEnabled(false);

        try {
            for (UIManager.LookAndFeelInfo info : UIManager.getInstalledLookAndFeels()) {
                if ("Nimbus".equals(info.getName())) {
                    UIManager.setLookAndFeel(info.getClassName());
                    break;
                }
            }
        } catch (Exception e) {
            // If Nimbus is not available, you can set the GUI to another look and feel.
            logger.warn("Failed to set look and feel to Nimbus", e);
        }
        try {
            LwjglCustomViewPort lwjglCustomViewPort = new LwjglCustomViewPort();
            Collection<EngineSubsystem> subsystemList = Lists.<EngineSubsystem>newArrayList(new LwjglGraphics(), new LwjglTimer(), new LwjglAudio(), new LwjglInput(),
                    lwjglCustomViewPort);

            PathManager.getInstance().useDefaultHomePath();

            engine = new TerasologyEngine(subsystemList);
            sceneProperties = new SceneProperties(engine);
            mainWindow = new MainWindow(this, engine);
            lwjglCustomViewPort.setCustomViewport(mainWindow.getViewport());

            engine.setHibernationAllowed(false);
            engine.subscribeToStateChange(mainWindow);

            engine.run(new StateMainMenu());
        } catch (Throwable t) {
            logger.error("Uncaught Exception", t);
        }
    }

    public GameEngine getEngine() {
        return engine;
    }

    public MainWindow getMainWindow() {
        return mainWindow;
    }

    public SceneProperties getSceneProperties() {
        return sceneProperties;
    }
}


File: engine/src/main/java/org/terasology/engine/EngineStatus.java
/*
 * Copyright 2015 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine;

/**
 * Engine Status provides the current status of the engine - what it is doing, at a higher granularity than just running. This can be used by external and internal observers
 * to report on the state of the engine, such as splash screens/loading screens.
 */
public interface EngineStatus {

    /**
     * @return The description of the status
     */
    String getDescription();

    /**
     * @return Whether this is a status that "progresses" such as loading, with a known completion point
     */
    boolean isProgressing();

    /**
     * @return The progress of this status, between 0 and 1 inclusive where 1 is complete and 0 is just started.
     */
    float getProgress();
}


File: engine/src/main/java/org/terasology/engine/TerasologyEngine.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.terasology.engine;

import com.google.api.client.repackaged.com.google.common.base.Preconditions;
import com.google.common.base.Stopwatch;
import com.google.common.collect.Queues;
import com.google.common.collect.Sets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.assets.AssetFactory;
import org.terasology.assets.management.AssetManager;
import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.config.RenderingConfig;
import org.terasology.context.Context;
import org.terasology.context.internal.ContextImpl;
import org.terasology.engine.bootstrap.EnvironmentSwitchHandler;
import org.terasology.engine.modes.GameState;
import org.terasology.engine.module.ModuleManager;
import org.terasology.engine.module.ModuleManagerImpl;
import org.terasology.engine.paths.PathManager;
import org.terasology.engine.subsystem.DisplayDevice;
import org.terasology.engine.subsystem.EngineSubsystem;
import org.terasology.engine.subsystem.RenderingSubsystemFactory;
import org.terasology.engine.subsystem.ThreadManager;
import org.terasology.engine.subsystem.ThreadManagerSubsystem;
import org.terasology.entitySystem.prefab.Prefab;
import org.terasology.entitySystem.prefab.PrefabData;
import org.terasology.entitySystem.prefab.internal.PojoPrefab;
import org.terasology.game.Game;
import org.terasology.identity.CertificateGenerator;
import org.terasology.identity.CertificatePair;
import org.terasology.identity.PrivateIdentityCertificate;
import org.terasology.identity.PublicIdentityCertificate;
import org.terasology.input.InputSystem;
import org.terasology.logic.behavior.asset.BehaviorTree;
import org.terasology.logic.behavior.asset.BehaviorTreeData;
import org.terasology.logic.console.commandSystem.adapter.ParameterAdapterManager;
import org.terasology.monitoring.Activity;
import org.terasology.monitoring.PerformanceMonitor;
import org.terasology.monitoring.gui.AdvancedMonitor;
import org.terasology.network.NetworkSystem;
import org.terasology.network.internal.NetworkSystemImpl;
import org.terasology.persistence.typeHandling.TypeSerializationLibrary;
import org.terasology.physics.CollisionGroupManager;
import org.terasology.reflection.copy.CopyStrategyLibrary;
import org.terasology.reflection.reflect.ReflectFactory;
import org.terasology.reflection.reflect.ReflectionReflectFactory;
import org.terasology.registry.CoreRegistry;
import org.terasology.rendering.nui.asset.UIData;
import org.terasology.rendering.nui.asset.UIElement;
import org.terasology.rendering.nui.skin.UISkin;
import org.terasology.rendering.nui.skin.UISkinData;
import org.terasology.version.TerasologyVersion;
import org.terasology.world.block.family.BlockFamilyFactoryRegistry;
import org.terasology.world.block.family.DefaultBlockFamilyFactoryRegistry;
import org.terasology.world.block.loader.BlockFamilyDefinition;
import org.terasology.world.block.loader.BlockFamilyDefinitionData;
import org.terasology.world.block.loader.BlockFamilyDefinitionFormat;
import org.terasology.world.block.shapes.BlockShape;
import org.terasology.world.block.shapes.BlockShapeData;
import org.terasology.world.block.shapes.BlockShapeImpl;
import org.terasology.world.block.sounds.BlockSounds;
import org.terasology.world.block.sounds.BlockSoundsData;
import org.terasology.world.block.tiles.BlockTile;
import org.terasology.world.block.tiles.TileData;
import org.terasology.world.generator.internal.WorldGeneratorManager;

import java.io.IOException;
import java.nio.file.Files;
import java.util.Collection;
import java.util.Deque;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.TimeUnit;

/**
 * @author Immortius
 *         <p>
 *         This GameEngine implementation is the heart of Terasology.
 *         <p>
 *         It first takes care of making a number of application-wide initializations (see init()
 *         method). It then provides a main game loop (see run() method) characterized by a number
 *         of mutually exclusive {@link GameState}s. The current GameState is updated each
 *         frame, and a change of state (see changeState() method) can be requested at any time - the
 *         switch will occur cleanly between frames. Interested parties can be notified of GameState
 *         changes by using the subscribeToStateChange() method.
 *         <p>
 *         At this stage the engine also provides a number of utility methods (see submitTask() and
 *         hasMouseFocus() to name a few) but they might be moved elsewhere.
 *         <p>
 *         Special mention must be made in regard to EngineSubsystems. An {@link EngineSubsystem}
 *         is a pluggable low-level component of the engine, that is processed every frame - like
 *         rendering or audio. A list of EngineSubsystems is provided in input to the engine's
 *         constructor. Different sets of Subsystems can significantly change the behaviour of
 *         the engine, i.e. providing a "no-frills" server in one case or a full-graphics client
 *         in another.
 */
public class TerasologyEngine implements GameEngine {

    private static final Logger logger = LoggerFactory.getLogger(TerasologyEngine.class);

    private static final int ONE_MEBIBYTE = 1024 * 1024;

    private Config config;
    private RenderingConfig renderingConfig;
    private EngineTime time;

    private GameState currentState;
    private GameState pendingState;
    private Set<StateChangeSubscriber> stateChangeSubscribers = Sets.newLinkedHashSet();

    private EngineStatus status = StandardGameStatus.UNSTARTED;
    private final List<EngineStatusSubscriber> statusSubscriberList = new CopyOnWriteArrayList<>();

    private volatile boolean shutdownRequested;
    private volatile boolean running;

    private boolean hibernationAllowed;

    private Deque<EngineSubsystem> subsystems;
    private ModuleAwareAssetTypeManager assetTypeManager;

    /**
     * Contains objects that life for the duration of this engine.
     */
    private Context context;

    /**
     * This constructor initializes the engine by initializing its systems,
     * subsystems and managers. It also verifies that some required systems
     * are up and running after they have been initialized.
     *
     * @param subsystems Typical subsystems lists contain graphics, timer,
     *                   audio and input subsystems.
     */
    public TerasologyEngine(Collection<EngineSubsystem> subsystems) {

        this.context = new ContextImpl();
        /*
         * We can't load the engine without core registry yet.
         * e.g. the statically created MaterialLoader needs the CoreRegistry to get the AssetManager.
         * And the engine loads assets while it gets created.
         */
        CoreRegistry.setContext(context);
        this.subsystems = Queues.newArrayDeque(subsystems);
        ThreadManagerSubsystem threadManager = new ThreadManagerSubsystem();
        this.subsystems.add(threadManager);
        context.put(ThreadManager.class, threadManager);
    }

    private void initialize() {
        Stopwatch totalInitTime = Stopwatch.createStarted();
        try {
            logger.info("Initializing Terasology...");
            logEnvironmentInfo();

            changeStatus(TerasologyEngineStatus.LOADING_CONFIG);
            initConfig();

            changeStatus(TerasologyEngineStatus.PREPARING_SUBSYSTEMS);
            preInitSubsystems();

            // time must be set here as it is required by some of the managers.
            verifyRequiredSystemIsRegistered(Time.class);
            time = (EngineTime) context.get(Time.class);

            GameThread.setToCurrentThread();

            changeStatus(TerasologyEngineStatus.INITIALIZING_SUBSYSTEMS);
            initSubsystems();

            initManagers();

            changeStatus(TerasologyEngineStatus.INITIALIZING_ASSET_MANAGEMENT);
            initAssets();
            EnvironmentSwitchHandler environmentSwitcher = new EnvironmentSwitchHandler();
            context.put(EnvironmentSwitchHandler.class, environmentSwitcher);

            environmentSwitcher.handleSwitchToGameEnvironment(context);

            postInitSubsystems();

            verifyRequiredSystemIsRegistered(DisplayDevice.class);
            verifyRequiredSystemIsRegistered(RenderingSubsystemFactory.class);
            verifyRequiredSystemIsRegistered(InputSystem.class);


            // TODO: Review - The advanced monitor shouldn't be hooked-in this way (see issue #692)
            initAdvancedMonitor();

            /**
             * Prevent objects being put in engine context after init phase. Engine states should use/create a
             * child context.
             */
            CoreRegistry.setContext(null);
        } catch (RuntimeException e) {
            logger.error("Failed to initialise Terasology", e);
            cleanup();
            throw e;
        }


        double seconds = 0.001 * totalInitTime.elapsed(TimeUnit.MILLISECONDS);
        logger.info("Initialization completed in {}sec.", String.format("%.2f", seconds));
    }

    /**
     * Logs software, environment and hardware information.
     */
    private void logEnvironmentInfo() {
        logger.info(TerasologyVersion.getInstance().toString());
        logger.info("Home path: {}", PathManager.getInstance().getHomePath());
        logger.info("Install path: {}", PathManager.getInstance().getInstallPath());
        logger.info("Java: {} in {}", System.getProperty("java.version"), System.getProperty("java.home"));
        logger.info("Java VM: {}, version: {}", System.getProperty("java.vm.name"), System.getProperty("java.vm.version"));
        logger.info("OS: {}, arch: {}, version: {}", System.getProperty("os.name"), System.getProperty("os.arch"), System.getProperty("os.version"));
        logger.info("Max. Memory: {} MiB", Runtime.getRuntime().maxMemory() / ONE_MEBIBYTE);
        logger.info("Processors: {}", Runtime.getRuntime().availableProcessors());
    }

    private void initConfig() {
        if (Files.isRegularFile(Config.getConfigFile())) {
            try {
                config = Config.load(Config.getConfigFile());
            } catch (IOException e) {
                logger.error("Failed to load config", e);
                config = new Config();
            }
        } else {
            config = new Config();
        }
        if (!config.getDefaultModSelection().hasModule(TerasologyConstants.CORE_GAMEPLAY_MODULE)) {
            config.getDefaultModSelection().addModule(TerasologyConstants.CORE_GAMEPLAY_MODULE);
        }

        if (!validateServerIdentity()) {
            CertificateGenerator generator = new CertificateGenerator();
            CertificatePair serverIdentity = generator.generateSelfSigned();
            config.getSecurity().setServerCredentials(serverIdentity.getPublicCert(), serverIdentity.getPrivateCert());
            config.save();
        }

        renderingConfig = config.getRendering();
        logger.info("Video Settings: " + renderingConfig.toString());
        context.put(Config.class, config);
    }

    private boolean validateServerIdentity() {
        PrivateIdentityCertificate privateCert = config.getSecurity().getServerPrivateCertificate();
        PublicIdentityCertificate publicCert = config.getSecurity().getServerPublicCertificate();

        if (privateCert == null || publicCert == null) {
            return false;
        }

        // Validate the signature
        if (!publicCert.verifySelfSigned()) {
            logger.error("Server signature is not self signed! Generating new server identity.");
            return false;
        }

        return true;
    }

    /**
     * Gives a chance to subsystems to do something BEFORE managers and Time are initialized.
     */
    private void preInitSubsystems() {
        for (EngineSubsystem subsystem : getSubsystems()) {
            subsystem.preInitialise(context);
        }
    }

    private void initSubsystems() {
        for (EngineSubsystem subsystem : getSubsystems()) {
            subsystem.initialise(context);
        }
    }

    /**
     * Gives a chance to subsystems to do something AFTER managers and Time are initialized.
     */
    private void postInitSubsystems() {
        for (EngineSubsystem subsystem : getSubsystems()) {
            subsystem.postInitialise(context);
        }
    }

    /**
     * Verifies that a required class is available through the core registry.
     *
     * @param clazz The required type, i.e. Time.class
     * @throws IllegalStateException Details the required system that has not been registered.
     */
    private void verifyRequiredSystemIsRegistered(Class<?> clazz) {
        if (context.get(clazz) == null) {
            throw new IllegalStateException(clazz.getSimpleName() + " not registered as a core system.");
        }
    }

    private void initManagers() {

        changeStatus(TerasologyEngineStatus.INITIALIZING_MODULE_MANAGER);
        ModuleManager moduleManager = new ModuleManagerImpl();
        context.put(ModuleManager.class, moduleManager);

        changeStatus(TerasologyEngineStatus.INITIALIZING_LOWLEVEL_OBJECT_MANIPULATION);
        ReflectFactory reflectFactory = new ReflectionReflectFactory();
        context.put(ReflectFactory.class, reflectFactory);

        CopyStrategyLibrary copyStrategyLibrary = new CopyStrategyLibrary(reflectFactory);
        context.put(CopyStrategyLibrary.class, copyStrategyLibrary);
        context.put(TypeSerializationLibrary.class, new TypeSerializationLibrary(reflectFactory,
                copyStrategyLibrary));

        changeStatus(TerasologyEngineStatus.INITIALIZING_ASSET_TYPES);
        assetTypeManager = new ModuleAwareAssetTypeManager();
        context.put(ModuleAwareAssetTypeManager.class, assetTypeManager);
        context.put(AssetManager.class, assetTypeManager.getAssetManager());
        context.put(CollisionGroupManager.class, new CollisionGroupManager());
        context.put(WorldGeneratorManager.class, new WorldGeneratorManager(context));
        context.put(ParameterAdapterManager.class, ParameterAdapterManager.createCore());
        context.put(NetworkSystem.class, new NetworkSystemImpl(time, context));
        context.put(Game.class, new Game(this, time));
    }

    /**
     * The Advanced Monitor is a display opening in a separate window
     * allowing for monitoring of Threads, Chunks and Performance.
     */
    private void initAdvancedMonitor() {
        if (config.getSystem().isMonitoringEnabled()) {
            new AdvancedMonitor().setVisible(true);
        }
    }

    private void initAssets() {
        DefaultBlockFamilyFactoryRegistry familyFactoryRegistry = new DefaultBlockFamilyFactoryRegistry();
        context.put(BlockFamilyFactoryRegistry.class, familyFactoryRegistry);

        // cast lambdas explicitly to avoid inconsistent compiler behavior wrt. type inference
        assetTypeManager.registerCoreAssetType(Prefab.class,
                (AssetFactory<Prefab, PrefabData>) PojoPrefab::new, false, "prefabs");
        assetTypeManager.registerCoreAssetType(BlockShape.class,
                (AssetFactory<BlockShape, BlockShapeData>) BlockShapeImpl::new, "shapes");
        assetTypeManager.registerCoreAssetType(BlockSounds.class,
                (AssetFactory<BlockSounds, BlockSoundsData>) BlockSounds::new, "blockSounds");
        assetTypeManager.registerCoreAssetType(BlockTile.class,
                (AssetFactory<BlockTile, TileData>) BlockTile::new, "blockTiles");
        assetTypeManager.registerCoreAssetType(BlockFamilyDefinition.class,
                (AssetFactory<BlockFamilyDefinition, BlockFamilyDefinitionData>) BlockFamilyDefinition::new, "blocks");
        assetTypeManager.registerCoreFormat(BlockFamilyDefinition.class,
                new BlockFamilyDefinitionFormat(assetTypeManager.getAssetManager(), familyFactoryRegistry));
        assetTypeManager.registerCoreAssetType(UISkin.class,
                (AssetFactory<UISkin, UISkinData>) UISkin::new, "skins");
        assetTypeManager.registerCoreAssetType(BehaviorTree.class,
                (AssetFactory<BehaviorTree, BehaviorTreeData>) BehaviorTree::new, false, "behaviors");
        assetTypeManager.registerCoreAssetType(UIElement.class,
                (AssetFactory<UIElement, UIData>) UIElement::new, "ui");

        for (EngineSubsystem subsystem : subsystems) {
            subsystem.registerCoreAssetTypes(assetTypeManager);
        }
    }

    @Override
    public EngineStatus getStatus() {
        return status;
    }

    @Override
    public void subscribe(EngineStatusSubscriber subscriber) {
        statusSubscriberList.add(subscriber);
    }

    @Override
    public void unsubscribe(EngineStatusSubscriber subscriber) {
        statusSubscriberList.remove(subscriber);
    }

    private void changeStatus(EngineStatus newStatus) {
        status = newStatus;
        for (EngineStatusSubscriber subscriber : statusSubscriberList) {
            subscriber.onEngineStatusChanged(newStatus);
        }
    }

    /**
     * Runs the engine, including its main loop. This method is called only once per
     * application startup, which is the reason the GameState provided is the -initial-
     * state rather than a generic game state.
     *
     * @param initialState In at least one context (the PC facade) the GameState
     *                     implementation provided as input may vary, depending if
     *                     the application has or hasn't been started headless.
     */
    @Override
    public synchronized void run(GameState initialState) {
        Preconditions.checkState(!running);
        running = true;
        initialize();
        changeStatus(StandardGameStatus.RUNNING);

        try {
            context.put(GameEngine.class, this);
            changeState(initialState);
            Thread.currentThread().setPriority(Thread.MAX_PRIORITY);

            mainLoop(); // -THE- MAIN LOOP. Most of the application time and resources are spent here.
        } catch (RuntimeException e) {
            logger.error("Uncaught exception, attempting clean game shutdown", e);
            throw e;
        } finally {
            try {
                cleanup();
            } catch (RuntimeException t) {
                logger.error("Clean game shutdown after an uncaught exception failed", t);
            }
            running = false;
            shutdownRequested = false;
            changeStatus(StandardGameStatus.UNSTARTED);
        }
    }

    /**
     * The main loop runs until the EngineState is set back to INITIALIZED by shutdown()
     * or until the OS requests the application's window to be closed. Engine cleanup
     * and disposal occur afterwards.
     */
    private void mainLoop() {
        NetworkSystem networkSystem = context.get(NetworkSystem.class);

        DisplayDevice display = context.get(DisplayDevice.class);

        PerformanceMonitor.startActivity("Other");
        // MAIN GAME LOOP
        while (!shutdownRequested && !display.isCloseRequested()) {

            long totalDelta;
            float updateDelta;
            float subsystemsDelta;

            // Only process rendering and updating once a second
            if (!display.hasFocus() && isHibernationAllowed()) {
                time.setPaused(true);
                Iterator<Float> updateCycles = time.tick();
                while (updateCycles.hasNext()) {
                    updateCycles.next();
                }
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    logger.warn("Display inactivity sleep interrupted", e);
                }

                display.processMessages();
                time.setPaused(false);
                continue;
            }

            assetTypeManager.reloadChangedOnDisk();

            processPendingState();

            if (currentState == null) {
                shutdown();
                break;
            }

            Iterator<Float> updateCycles = time.tick();

            try (Activity ignored = PerformanceMonitor.startActivity("Network Update")) {
                networkSystem.update();
            }

            totalDelta = 0;
            while (updateCycles.hasNext()) {
                updateDelta = updateCycles.next(); // gameTime gets updated here!
                totalDelta += time.getDeltaInMs();
                try (Activity ignored = PerformanceMonitor.startActivity("Main Update")) {
                    currentState.update(updateDelta);
                }
            }

            subsystemsDelta = totalDelta / 1000f;

            for (EngineSubsystem subsystem : getSubsystems()) {
                try (Activity ignored = PerformanceMonitor.startActivity(subsystem.getClass().getSimpleName())) {
                    subsystem.preUpdate(currentState, subsystemsDelta);
                }
            }

            // Waiting processes are set by modules via GameThread.a/synch() methods.
            GameThread.processWaitingProcesses();

            for (EngineSubsystem subsystem : getSubsystems()) {
                try (Activity ignored = PerformanceMonitor.startActivity(subsystem.getClass().getSimpleName())) {
                    subsystem.postUpdate(currentState, subsystemsDelta);
                }
            }

            PerformanceMonitor.rollCycle();
            PerformanceMonitor.startActivity("Other");
        }
        PerformanceMonitor.endActivity();
    }

    private void cleanup() {
        logger.info("Shutting down Terasology...");
        changeStatus(StandardGameStatus.SHUTTING_DOWN);

        Iterator<EngineSubsystem> shutdownIter = subsystems.descendingIterator();
        while (shutdownIter.hasNext()) {
            EngineSubsystem subsystem = shutdownIter.next();
            subsystem.shutdown(config);
        }

        config.save();
        if (currentState != null) {
            currentState.dispose();
            currentState = null;
        }

        Iterator<EngineSubsystem> disposeIter = subsystems.descendingIterator();
        while (disposeIter.hasNext()) {
            EngineSubsystem subsystem = disposeIter.next();
            try {
                subsystem.dispose();
            } catch (RuntimeException t) {
                logger.error("Unable to dispose subsystem {}", subsystem, t);
            }
        }
    }

    /**
     * Causes the main loop to stop at the end of the current frame, cleanly ending
     * the current GameState, all running task threads and disposing subsystems.
     */
    @Override
    public void shutdown() {
        shutdownRequested = true;
    }

    /**
     * Changes the game state, i.e. to switch from the MainMenu to Ingame via Loading screen
     * (each is a GameState). The change can be immediate, if there is no current game
     * state set, or scheduled, when a current state exists and the new state is stored as
     * pending. That been said, scheduled changes occurs in the main loop through the call
     * processStateChanges(). As such, from a user perspective in normal circumstances,
     * scheduled changes are likely to be perceived as immediate.
     */
    @Override
    public void changeState(GameState newState) {
        if (currentState != null) {
            pendingState = newState;    // scheduled change
        } else {
            switchState(newState);      // immediate change
        }
    }

    private void processPendingState() {
        if (pendingState != null) {
            switchState(pendingState);
            pendingState = null;
        }
    }

    private void switchState(GameState newState) {
        if (currentState != null) {
            currentState.dispose();
        }
        currentState = newState;
        LoggingContext.setGameState(newState);
        newState.init(this);
        for (StateChangeSubscriber subscriber : stateChangeSubscribers) {
            subscriber.onStateChange();
        }
        // drain input queues
        InputSystem inputSystem = context.get(InputSystem.class);
        inputSystem.getMouseDevice().getInputQueue();
        inputSystem.getKeyboard().getInputQueue();
    }

    @Override
    public boolean hasPendingState() {
        return pendingState != null;
    }

    @Override
    public GameState getState() {
        return currentState;
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    public Iterable<EngineSubsystem> getSubsystems() {
        return subsystems;
    }

    public boolean isFullscreen() {
        return renderingConfig.isFullscreen();
    }

    public void setFullscreen(boolean state) {
        if (renderingConfig.isFullscreen() != state) {
            renderingConfig.setFullscreen(state);
            DisplayDevice display = context.get(DisplayDevice.class);
            display.setFullscreen(state);
        }
    }

    @Override
    public boolean isHibernationAllowed() {
        return hibernationAllowed && currentState.isHibernationAllowed();
    }

    @Override
    public void setHibernationAllowed(boolean allowed) {
        this.hibernationAllowed = allowed;
    }

    @Override
    public void subscribeToStateChange(StateChangeSubscriber subscriber) {
        stateChangeSubscribers.add(subscriber);
    }

    @Override
    public void unsubscribeToStateChange(StateChangeSubscriber subscriber) {
        stateChangeSubscribers.remove(subscriber);
    }

    @Override
    public Context createChildContext() {
        return new ContextImpl(context);
    }

    /**
     * Allows it to obtain objects directly from the context of the game engine. It exists only for situations in
     * which no child context exists yet. If there is a child context then it automatically contains the objects of
     * the engine context. Thus normal code should just work with the (child) context that is available to it
     * instead of using this method.
     *
     * @return a object directly from the context of the game engine
     */
    public <T> T getFromEngineContext(Class<? extends T> type) {
        return context.get(type);
    }
}


File: engine/src/main/java/org/terasology/engine/TerasologyEngineStatus.java
/*
 * Copyright 2015 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine;

/**
 * An enum for describing the status of the engine, to be used in addition to the StandardGameStatuses
 */
public enum TerasologyEngineStatus implements EngineStatus {

    LOADING_CONFIG("Loading config..."),
    PREPARING_SUBSYSTEMS("Preparing Subsystems..."),
    INITIALIZING_ASSET_MANAGEMENT("Initializing Asset Management..."),
    INITIALIZING_SUBSYSTEMS("Initializing Subsystems..."),
    INITIALIZING_MODULE_MANAGER("Initializing Module Management..."),
    INITIALIZING_LOWLEVEL_OBJECT_MANIPULATION("Initializing low-level object manipulators..."),
    INITIALIZING_ASSET_TYPES("Initializing asset types...");

    private final String defaultDescription;

    private TerasologyEngineStatus(String defaultDescription) {
        this.defaultDescription = defaultDescription;
    }

    @Override
    public String getDescription() {
        return defaultDescription;
    }

    @Override
    public float getProgress() {
        return 0;
    }

    @Override
    public boolean isProgressing() {
        return false;
    }
}


File: engine/src/main/java/org/terasology/engine/subsystem/DisplayDevice.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem;

public interface DisplayDevice {

    boolean hasFocus();

    boolean isCloseRequested();

    void setFullscreen(boolean state);

    // TODO: this breaks the nice API we have so far.
    // From the lwjgl docs:
    //   Process operating system events.
    //   Call this to update the Display's state and to receive new input device events.
    //   This method is called from update(), so it is not necessary to call this method
    //   if update() is called periodically.
    void processMessages();

    boolean isHeadless();

    // TODO: another method that possibly doesn't need to exist, but I need to check with Immortius on this
    void prepareToRender();

}


File: engine/src/main/java/org/terasology/engine/subsystem/EngineSubsystem.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem;

import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.modes.GameState;

public interface EngineSubsystem {

    /**
     * Called on each system before initialisation
     */
    void preInitialise(Context context);

    /**
     * Called to initialise the system
     */
    void initialise(Context context);

    /**
     * Called to register any core asset types this system provides. This happens after initialise and before postInitialise
     *
     * @param assetTypeManager
     */
    void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager);

    /**
     * Called to do any final initialisation after asset types are registered.
     */
    void postInitialise(Context context);

    void preUpdate(GameState currentState, float delta);

    void postUpdate(GameState currentState, float delta);

    void shutdown(Config config);

    void dispose();

    void registerSystems(ComponentSystemManager componentSystemManager);
}


File: engine/src/main/java/org/terasology/engine/subsystem/headless/HeadlessAudio.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.headless;

import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.audio.AudioManager;
import org.terasology.audio.StaticSound;
import org.terasology.audio.StreamingSound;
import org.terasology.audio.nullAudio.NullAudioManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.modes.GameState;
import org.terasology.engine.subsystem.EngineSubsystem;

public class HeadlessAudio implements EngineSubsystem {

    private AudioManager audioManager;

    @Override
    public void preInitialise(Context context) {
    }

    @Override

    public void initialise(Context context) {
        initNoSound(context);
    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
        assetTypeManager.registerCoreAssetType(StaticSound.class, audioManager.getStaticSoundFactory(), "sounds");
        assetTypeManager.registerCoreAssetType(StreamingSound.class, audioManager.getStreamingSoundFactory(), "music");
    }

    @Override
    public void postInitialise(Context context) {
    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
        audioManager.update(delta);
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
        audioManager.dispose();
    }

    private void initNoSound(Context context) {
        audioManager = new NullAudioManager();
        context.put(AudioManager.class, audioManager);
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/engine/subsystem/headless/HeadlessGraphics.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.headless;

import org.terasology.assets.AssetFactory;
import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.modes.GameState;
import org.terasology.engine.subsystem.DisplayDevice;
import org.terasology.engine.subsystem.EngineSubsystem;
import org.terasology.engine.subsystem.RenderingSubsystemFactory;
import org.terasology.engine.subsystem.headless.assets.HeadlessMaterial;
import org.terasology.engine.subsystem.headless.assets.HeadlessMesh;
import org.terasology.engine.subsystem.headless.assets.HeadlessShader;
import org.terasology.engine.subsystem.headless.assets.HeadlessSkeletalMesh;
import org.terasology.engine.subsystem.headless.assets.HeadlessTexture;
import org.terasology.engine.subsystem.headless.device.HeadlessDisplayDevice;
import org.terasology.engine.subsystem.headless.renderer.HeadlessCanvasRenderer;
import org.terasology.engine.subsystem.headless.renderer.HeadlessRenderingSubsystemFactory;
import org.terasology.engine.subsystem.headless.renderer.ShaderManagerHeadless;
import org.terasology.rendering.ShaderManager;
import org.terasology.rendering.assets.animation.MeshAnimation;
import org.terasology.rendering.assets.animation.MeshAnimationData;
import org.terasology.rendering.assets.animation.MeshAnimationImpl;
import org.terasology.rendering.assets.atlas.Atlas;
import org.terasology.rendering.assets.atlas.AtlasData;
import org.terasology.rendering.assets.font.Font;
import org.terasology.rendering.assets.font.FontData;
import org.terasology.rendering.assets.font.FontImpl;
import org.terasology.rendering.assets.material.Material;
import org.terasology.rendering.assets.material.MaterialData;
import org.terasology.rendering.assets.mesh.Mesh;
import org.terasology.rendering.assets.mesh.MeshData;
import org.terasology.rendering.assets.shader.Shader;
import org.terasology.rendering.assets.shader.ShaderData;
import org.terasology.rendering.assets.skeletalmesh.SkeletalMesh;
import org.terasology.rendering.assets.skeletalmesh.SkeletalMeshData;
import org.terasology.rendering.assets.texture.PNGTextureFormat;
import org.terasology.rendering.assets.texture.Texture;
import org.terasology.rendering.assets.texture.TextureData;
import org.terasology.rendering.assets.texture.subtexture.Subtexture;
import org.terasology.rendering.assets.texture.subtexture.SubtextureData;
import org.terasology.rendering.nui.internal.CanvasRenderer;

public class HeadlessGraphics implements EngineSubsystem {

    @Override
    public void preInitialise(Context context) {
    }

    @Override
    public void initialise(Context context) {

    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
        assetTypeManager.registerCoreAssetType(Font.class, (AssetFactory<Font, FontData>) FontImpl::new, "fonts");
        assetTypeManager.registerCoreAssetType(Texture.class, (AssetFactory<Texture, TextureData>) HeadlessTexture::new, "textures", "fonts");
        assetTypeManager.registerCoreFormat(Texture.class, new PNGTextureFormat(Texture.FilterMode.NEAREST, path -> path.getName(2).toString().equals("textures")));
        assetTypeManager.registerCoreFormat(Texture.class, new PNGTextureFormat(Texture.FilterMode.LINEAR, path -> path.getName(2).toString().equals("fonts")));
        assetTypeManager.registerCoreAssetType(Shader.class, (AssetFactory<Shader, ShaderData>) HeadlessShader::new, "shaders");
        assetTypeManager.registerCoreAssetType(Material.class, (AssetFactory<Material, MaterialData>) HeadlessMaterial::new, "materials");
        assetTypeManager.registerCoreAssetType(Mesh.class, (AssetFactory<Mesh, MeshData>) HeadlessMesh::new, "mesh");
        assetTypeManager.registerCoreAssetType(SkeletalMesh.class, (AssetFactory<SkeletalMesh, SkeletalMeshData>) HeadlessSkeletalMesh::new, "skeletalMesh");
        assetTypeManager.registerCoreAssetType(MeshAnimation.class, (AssetFactory<MeshAnimation, MeshAnimationData>) MeshAnimationImpl::new, "animations");
        assetTypeManager.registerCoreAssetType(Atlas.class, (AssetFactory<Atlas, AtlasData>) Atlas::new, "atlas");
        assetTypeManager.registerCoreAssetType(Subtexture.class, (AssetFactory<Subtexture, SubtextureData>) Subtexture::new);
    }

    @Override
    public void postInitialise(Context context) {
        context.put(RenderingSubsystemFactory.class, new HeadlessRenderingSubsystemFactory());

        HeadlessDisplayDevice headlessDisplay = new HeadlessDisplayDevice();
        context.put(DisplayDevice.class, headlessDisplay);
        initHeadless(context);

        context.put(CanvasRenderer.class, new HeadlessCanvasRenderer());
    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
    }


    private void initHeadless(Context context) {
        context.put(ShaderManager.class, new ShaderManagerHeadless());
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/engine/subsystem/headless/HeadlessInput.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.headless;

import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.modes.GameState;
import org.terasology.engine.subsystem.EngineSubsystem;
import org.terasology.input.InputSystem;

public class HeadlessInput implements EngineSubsystem {

    @Override
    public void preInitialise(Context context) {
    }

    @Override
    public void initialise(Context context) {

    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
    }

    @Override
    public void postInitialise(Context context) {
        initControls(context);
    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
    }

    private void initControls(Context context) {
        InputSystem inputSystem = new InputSystem();
        context.put(InputSystem.class, inputSystem);
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/engine/subsystem/headless/HeadlessTimer.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.headless;

import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.EngineTime;
import org.terasology.engine.Time;
import org.terasology.engine.modes.GameState;
import org.terasology.engine.subsystem.EngineSubsystem;
import org.terasology.engine.subsystem.headless.device.TimeSystem;

public class HeadlessTimer implements EngineSubsystem {

    @Override
    public void preInitialise(Context context) {
        initTimer(context);
    }

    @Override
    public void initialise(Context context) {

    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
    }

    @Override
    public void postInitialise(Context context) {

    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
    }

    private void initTimer(Context context) {
        EngineTime time = new TimeSystem();
        context.put(Time.class, time);
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/engine/subsystem/headless/device/HeadlessDisplayDevice.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.headless.device;

import org.terasology.engine.subsystem.DisplayDevice;

public class HeadlessDisplayDevice implements DisplayDevice {

    public HeadlessDisplayDevice() {
    }

    @Override
    public boolean isHeadless() {
        return true;
    }

    @Override
    public boolean hasFocus() {

        return true;
    }

    @Override
    public boolean isCloseRequested() {
        return false;
    }

    @Override
    public void setFullscreen(boolean state) {
    }

    @Override
    public void processMessages() {
    }

    @Override
    public void prepareToRender() {
    }
}


File: engine/src/main/java/org/terasology/engine/subsystem/lwjgl/LwjglAudio.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.lwjgl;

import org.lwjgl.LWJGLException;
import org.lwjgl.openal.OpenALException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.audio.AudioManager;
import org.terasology.audio.StaticSound;
import org.terasology.audio.StreamingSound;
import org.terasology.audio.nullAudio.NullAudioManager;
import org.terasology.audio.openAL.OpenALManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.modes.GameState;

public class LwjglAudio extends BaseLwjglSubsystem {

    private static final Logger logger = LoggerFactory.getLogger(LwjglAudio.class);

    private AudioManager audioManager;

    @Override
    public synchronized void preInitialise(Context context) {
        super.preInitialise(context);
    }

    @Override
    public void initialise(Context context) {
        initOpenAL(context);
    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
        assetTypeManager.registerCoreAssetType(StaticSound.class, audioManager.getStaticSoundFactory(), "sounds");
        assetTypeManager.registerCoreAssetType(StreamingSound.class, audioManager.getStreamingSoundFactory(), "music");
    }

    @Override
    public void postInitialise(Context context) {

    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
        audioManager.update(delta);
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
        if (audioManager != null) {
            audioManager.dispose();
        }
    }

    private void initOpenAL(Context context) {
                Config config = context.get(Config.class);
                try {
            audioManager = new OpenALManager(config.getAudio());
        } catch (LWJGLException | OpenALException e) {
            logger.warn("Could not load OpenAL manager - sound is disabled", e);
            audioManager = new NullAudioManager();
        }
        context.put(AudioManager.class, audioManager);
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/engine/subsystem/lwjgl/LwjglDisplayDevice.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.lwjgl;

import org.lwjgl.LWJGLException;
import org.lwjgl.opengl.Display;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.subsystem.DisplayDevice;

import static org.lwjgl.opengl.GL11.GL_COLOR_BUFFER_BIT;
import static org.lwjgl.opengl.GL11.GL_DEPTH_BUFFER_BIT;
import static org.lwjgl.opengl.GL11.glClear;
import static org.lwjgl.opengl.GL11.glLoadIdentity;
import static org.lwjgl.opengl.GL11.glViewport;

public class LwjglDisplayDevice implements DisplayDevice {

    private static final Logger logger = LoggerFactory.getLogger(LwjglDisplayDevice.class);
    private Context context;

    public LwjglDisplayDevice(Context context) {
        this.context = context;
    }

    @Override
    public boolean hasFocus() {
        return Display.isActive();
    }

    @Override
    public boolean isCloseRequested() {
        return Display.isCloseRequested();
    }

    @Override
    public void setFullscreen(boolean state) {
        setFullscreen(state, true);
    }

    void setFullscreen(boolean state, boolean resize) {
        try {
            if (state) {
                Display.setDisplayMode(Display.getDesktopDisplayMode());
                Display.setFullscreen(true);
            } else {
                Config config = context.get(Config.class);
                Display.setDisplayMode(config.getRendering().getDisplayMode());
                Display.setResizable(true);
            }
        } catch (LWJGLException e) {
            throw new RuntimeException("Can not initialize graphics device.", e);
        }
        if (resize) {
            glViewport(0, 0, Display.getWidth(), Display.getHeight());
        }
    }

    @Override
    public void processMessages() {
        Display.processMessages();
    }

    @Override
    public boolean isHeadless() {
        return false;
    }

    @Override
    public void prepareToRender() {
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        glLoadIdentity();
    }
}


File: engine/src/main/java/org/terasology/engine/subsystem/lwjgl/LwjglGraphics.java
/*
 * Copyright 2015 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.lwjgl;

import com.google.common.collect.Lists;
import com.google.common.collect.Queues;
import org.lwjgl.LWJGLException;
import org.lwjgl.opengl.ContextAttribs;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL12;
import org.lwjgl.opengl.GL43;
import org.lwjgl.opengl.GLContext;
import org.lwjgl.opengl.KHRDebugCallback;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.assets.AssetFactory;
import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.config.RenderingConfig;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.GameThread;
import org.terasology.engine.modes.GameState;
import org.terasology.engine.subsystem.DisplayDevice;
import org.terasology.engine.subsystem.RenderingSubsystemFactory;
import org.terasology.rendering.ShaderManager;
import org.terasology.rendering.ShaderManagerLwjgl;
import org.terasology.rendering.assets.animation.MeshAnimation;
import org.terasology.rendering.assets.animation.MeshAnimationData;
import org.terasology.rendering.assets.animation.MeshAnimationImpl;
import org.terasology.rendering.assets.atlas.Atlas;
import org.terasology.rendering.assets.atlas.AtlasData;
import org.terasology.rendering.assets.font.Font;
import org.terasology.rendering.assets.font.FontData;
import org.terasology.rendering.assets.font.FontImpl;
import org.terasology.rendering.assets.material.Material;
import org.terasology.rendering.assets.material.MaterialData;
import org.terasology.rendering.assets.mesh.Mesh;
import org.terasology.rendering.assets.mesh.MeshData;
import org.terasology.rendering.assets.shader.Shader;
import org.terasology.rendering.assets.shader.ShaderData;
import org.terasology.rendering.assets.skeletalmesh.SkeletalMesh;
import org.terasology.rendering.assets.skeletalmesh.SkeletalMeshData;
import org.terasology.rendering.assets.texture.PNGTextureFormat;
import org.terasology.rendering.assets.texture.Texture;
import org.terasology.rendering.assets.texture.TextureData;
import org.terasology.rendering.assets.texture.TextureUtil;
import org.terasology.rendering.assets.texture.subtexture.Subtexture;
import org.terasology.rendering.assets.texture.subtexture.SubtextureData;
import org.terasology.rendering.nui.internal.CanvasRenderer;
import org.terasology.rendering.nui.internal.LwjglCanvasRenderer;
import org.terasology.rendering.opengl.GLSLMaterial;
import org.terasology.rendering.opengl.GLSLShader;
import org.terasology.rendering.opengl.OpenGLMesh;
import org.terasology.rendering.opengl.OpenGLSkeletalMesh;
import org.terasology.rendering.opengl.OpenGLTexture;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.List;
import java.util.concurrent.BlockingDeque;
import java.util.function.Consumer;

import static org.lwjgl.opengl.GL11.GL_CULL_FACE;
import static org.lwjgl.opengl.GL11.GL_DEPTH_TEST;
import static org.lwjgl.opengl.GL11.GL_LEQUAL;
import static org.lwjgl.opengl.GL11.GL_NORMALIZE;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_2D;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_WRAP_S;
import static org.lwjgl.opengl.GL11.GL_TEXTURE_WRAP_T;
import static org.lwjgl.opengl.GL11.glBindTexture;
import static org.lwjgl.opengl.GL11.glDeleteTextures;
import static org.lwjgl.opengl.GL11.glDepthFunc;
import static org.lwjgl.opengl.GL11.glEnable;
import static org.lwjgl.opengl.GL11.glGenTextures;
import static org.lwjgl.opengl.GL11.glTexParameterf;
import static org.lwjgl.opengl.GL11.glViewport;

public class LwjglGraphics extends BaseLwjglSubsystem {
    private static final Logger logger = LoggerFactory.getLogger(LwjglGraphics.class);

    private GLBufferPool bufferPool = new GLBufferPool(false);

    private BlockingDeque<Runnable> displayThreadActions = Queues.newLinkedBlockingDeque();

    private Context context;

    @Override
    public void initialise(Context newContext) {
           this.context = newContext;
    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {

        // cast lambdas explicitly to avoid inconsistent compiler behavior wrt. type inference
        assetTypeManager.registerCoreAssetType(Font.class,
                (AssetFactory<Font, FontData>) FontImpl::new, "fonts");
        assetTypeManager.registerCoreAssetType(Texture.class, (AssetFactory<Texture, TextureData>)
                (urn, assetType, data) -> (new OpenGLTexture(urn, assetType, data, this)), "textures", "fonts");
        assetTypeManager.registerCoreFormat(Texture.class,
                new PNGTextureFormat(Texture.FilterMode.NEAREST, path -> path.getName(2).toString().equals("textures")));
        assetTypeManager.registerCoreFormat(Texture.class,
                new PNGTextureFormat(Texture.FilterMode.LINEAR, path -> path.getName(2).toString().equals("fonts")));
        assetTypeManager.registerCoreAssetType(Shader.class,
                (AssetFactory<Shader, ShaderData>) GLSLShader::new, "shaders");
        assetTypeManager.registerCoreAssetType(Material.class,
                (AssetFactory<Material, MaterialData>) GLSLMaterial::new, "materials");
        assetTypeManager.registerCoreAssetType(Mesh.class, (AssetFactory<Mesh, MeshData>)
                (urn, assetType, data) -> new OpenGLMesh(urn, assetType, bufferPool, data), "mesh");
        assetTypeManager.registerCoreAssetType(SkeletalMesh.class, (AssetFactory<SkeletalMesh, SkeletalMeshData>)
                (urn, assetType, data) -> new OpenGLSkeletalMesh(urn, assetType, data, bufferPool), "skeletalMesh");
        assetTypeManager.registerCoreAssetType(MeshAnimation.class,
                (AssetFactory<MeshAnimation, MeshAnimationData>) MeshAnimationImpl::new, "animations");
        assetTypeManager.registerCoreAssetType(Atlas.class,
                (AssetFactory<Atlas, AtlasData>) Atlas::new, "atlas");
        assetTypeManager.registerCoreAssetType(Subtexture.class,
                (AssetFactory<Subtexture, SubtextureData>) Subtexture::new);
    }

    @Override
    public void postInitialise(Context newContext) {
        this.context = newContext;
        context.put(RenderingSubsystemFactory.class, new LwjglRenderingSubsystemFactory(bufferPool));

        LwjglDisplayDevice lwjglDisplay = new LwjglDisplayDevice(context);
        context.put(DisplayDevice.class, lwjglDisplay);

        initDisplay(context.get(Config.class), lwjglDisplay);
        initOpenGL(context);

        context.put(CanvasRenderer.class, new LwjglCanvasRenderer(context));
    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
        Display.update();

        if (!displayThreadActions.isEmpty()) {
            List<Runnable> actions = Lists.newArrayListWithExpectedSize(displayThreadActions.size());
            displayThreadActions.drainTo(actions);
            actions.forEach(Runnable::run);
        }

        int frameLimit = context.get(Config.class).getRendering().getFrameLimit();
        if (frameLimit > 0) {
            Display.sync(frameLimit);
        }
        currentState.render();

        if (Display.wasResized()) {
            glViewport(0, 0, Display.getWidth(), Display.getHeight());
        }
    }

    @Override
    public void shutdown(Config config) {
        if (Display.isCreated() && !Display.isFullscreen() && Display.isVisible()) {
            config.getRendering().setWindowPosX(Display.getX());
            config.getRendering().setWindowPosY(Display.getY());
        }
    }

    @Override
    public void dispose() {
        Display.destroy();
    }

    private void initDisplay(Config config, LwjglDisplayDevice lwjglDisplay) {
        try {
            lwjglDisplay.setFullscreen(config.getRendering().isFullscreen(), false);

            RenderingConfig rc = config.getRendering();
            Display.setLocation(rc.getWindowPosX(), rc.getWindowPosY());
            Display.setTitle("Terasology" + " | " + "Pre Alpha");
            try {

                String root = "org/terasology/icons/";
                ClassLoader classLoader = getClass().getClassLoader();

                BufferedImage icon16 = ImageIO.read(classLoader.getResourceAsStream(root + "gooey_sweet_16.png"));
                BufferedImage icon32 = ImageIO.read(classLoader.getResourceAsStream(root + "gooey_sweet_32.png"));
                BufferedImage icon64 = ImageIO.read(classLoader.getResourceAsStream(root + "gooey_sweet_64.png"));
                BufferedImage icon128 = ImageIO.read(classLoader.getResourceAsStream(root + "gooey_sweet_128.png"));

                Display.setIcon(new ByteBuffer[]{
                        TextureUtil.convertToByteBuffer(icon16),
                        TextureUtil.convertToByteBuffer(icon32),
                        TextureUtil.convertToByteBuffer(icon64),
                        TextureUtil.convertToByteBuffer(icon128)
                });

            } catch (IOException | IllegalArgumentException e) {
                logger.warn("Could not set icon", e);
            }

            if (config.getRendering().getDebug().isEnabled()) {
                try {
                    ContextAttribs ctxAttribs = new ContextAttribs().withDebug(true);
                    Display.create(config.getRendering().getPixelFormat(), ctxAttribs);

                    GL43.glDebugMessageCallback(new KHRDebugCallback(new DebugCallback()));
                } catch (LWJGLException e) {
                    logger.warn("Unable to create an OpenGL debug context. Maybe your graphics card does not support it.", e);
                    Display.create(rc.getPixelFormat()); // Create a normal context instead
                }

            } else {
                Display.create(rc.getPixelFormat());
            }

            Display.setVSyncEnabled(rc.isVSync());
        } catch (LWJGLException e) {
            throw new RuntimeException("Can not initialize graphics device.", e);
        }
    }

    private void initOpenGL(Context currentContext) {
        checkOpenGL();
        glViewport(0, 0, Display.getWidth(), Display.getHeight());
        initOpenGLParams();
        currentContext.put(ShaderManager.class, new ShaderManagerLwjgl());
    }

    private void checkOpenGL() {
        boolean[] requiredCapabilities = {
                GLContext.getCapabilities().OpenGL12,
                GLContext.getCapabilities().OpenGL14,
                GLContext.getCapabilities().OpenGL15,
                GLContext.getCapabilities().OpenGL20,
                GLContext.getCapabilities().OpenGL21,   // needed as we use GLSL 1.20

                GLContext.getCapabilities().GL_ARB_framebuffer_object,  // Extensions eventually included in
                GLContext.getCapabilities().GL_ARB_texture_float,       // OpenGl 3.0 according to
                GLContext.getCapabilities().GL_ARB_half_float_pixel};   // http://en.wikipedia.org/wiki/OpenGL#OpenGL_3.0

        String[] capabilityNames = {"OpenGL12",
                "OpenGL14",
                "OpenGL15",
                "OpenGL20",
                "OpenGL21",
                "GL_ARB_framebuffer_object",
                "GL_ARB_texture_float",
                "GL_ARB_half_float_pixel"};

        boolean canRunTheGame = true;
        String missingCapabilitiesMessage = "";

        for (int index = 0; index < requiredCapabilities.length; index++) {
            if (!requiredCapabilities[index]) {
                missingCapabilitiesMessage += "    - " + capabilityNames[index] + "\n";
                canRunTheGame = false;
            }
        }

        if (!canRunTheGame) {
            String completeErrorMessage = completeErrorMessage(missingCapabilitiesMessage);
            throw new IllegalStateException(completeErrorMessage);
        }
    }

    private String completeErrorMessage(String errorMessage) {
        return "\n" +
                "\nThe following OpenGL versions/extensions are required but are not supported by your GPU driver:\n" +
                "\n" +
                errorMessage +
                "\n" +
                "GPU Information:\n" +
                "\n" +
                "    Vendor:  " + GL11.glGetString(GL11.GL_VENDOR) + "\n" +
                "    Model:   " + GL11.glGetString(GL11.GL_RENDERER) + "\n" +
                "    Driver:  " + GL11.glGetString(GL11.GL_VERSION) + "\n" +
                "\n" +
                "Try updating the driver to the latest version available.\n" +
                "If that fails you might need to use a different GPU (graphics card). Sorry!\n";
    }

    public void initOpenGLParams() {
        glEnable(GL_CULL_FACE);
        glEnable(GL_DEPTH_TEST);
        glEnable(GL_NORMALIZE);
        glDepthFunc(GL_LEQUAL);
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

    public void asynchToDisplayThread(Runnable action) {
        if (GameThread.isCurrentThread()) {
            action.run();
        } else {
            displayThreadActions.add(action);
        }
    }

    public void createTexture3D(ByteBuffer alignedBuffer, Texture.WrapMode wrapMode, Texture.FilterMode filterMode,
                                int size, Consumer<Integer> idConsumer) {
        asynchToDisplayThread(() -> {
            int id = glGenTextures();
            reloadTexture3D(id, alignedBuffer, wrapMode, filterMode, size);
            idConsumer.accept(id);
        });
    }

    public void reloadTexture3D(int id, ByteBuffer alignedBuffer, Texture.WrapMode wrapMode, Texture.FilterMode filterMode, int size) {
        asynchToDisplayThread(() -> {
            glBindTexture(GL12.GL_TEXTURE_3D, id);

            glTexParameterf(GL12.GL_TEXTURE_3D, GL_TEXTURE_WRAP_S, LwjglGraphicsUtil.getGLMode(wrapMode));
            glTexParameterf(GL12.GL_TEXTURE_3D, GL_TEXTURE_WRAP_T, LwjglGraphicsUtil.getGLMode(wrapMode));
            glTexParameterf(GL12.GL_TEXTURE_3D, GL12.GL_TEXTURE_WRAP_R, LwjglGraphicsUtil.getGLMode(wrapMode));

            GL11.glTexParameteri(GL12.GL_TEXTURE_3D, GL11.GL_TEXTURE_MIN_FILTER, LwjglGraphicsUtil.getGlMinFilter(filterMode));
            GL11.glTexParameteri(GL12.GL_TEXTURE_3D, GL11.GL_TEXTURE_MAG_FILTER, LwjglGraphicsUtil.getGlMagFilter(filterMode));

            GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
            GL11.glTexParameteri(GL12.GL_TEXTURE_3D, GL12.GL_TEXTURE_MAX_LEVEL, 0);

            GL12.glTexImage3D(GL12.GL_TEXTURE_3D, 0, GL11.GL_RGBA, size, size, size, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, alignedBuffer);
        });
    }

    public void createTexture2D(ByteBuffer[] buffers, Texture.WrapMode wrapMode, Texture.FilterMode filterMode, int width, int height, Consumer<Integer> idConsumer) {
        asynchToDisplayThread(() -> {
            int id = glGenTextures();
            reloadTexture2D(id, buffers, wrapMode, filterMode, width, height);
            idConsumer.accept(id);
        });
    }

    public void reloadTexture2D(int id, ByteBuffer[] buffers, Texture.WrapMode wrapMode, Texture.FilterMode filterMode, int width, int height) {
        asynchToDisplayThread(() -> {
            glBindTexture(GL11.GL_TEXTURE_2D, id);

            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, LwjglGraphicsUtil.getGLMode(wrapMode));
            glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, LwjglGraphicsUtil.getGLMode(wrapMode));
            GL11.glTexParameteri(GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, LwjglGraphicsUtil.getGlMinFilter(filterMode));
            GL11.glTexParameteri(GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, LwjglGraphicsUtil.getGlMagFilter(filterMode));
            GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 4);
            GL11.glTexParameteri(GL11.GL_TEXTURE_2D, GL12.GL_TEXTURE_MAX_LEVEL, buffers.length - 1);

            if (buffers.length > 0) {
                for (int i = 0; i < buffers.length; i++) {
                    GL11.glTexImage2D(GL11.GL_TEXTURE_2D, i, GL11.GL_RGBA, width >> i, height >> i, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buffers[i]);
                }
            } else {
                GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, width, height, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, (ByteBuffer) null);
            }
        });
    }

    public void disposeTexture(int id) {
        asynchToDisplayThread(() -> glDeleteTextures(id));
    }
}


File: engine/src/main/java/org/terasology/engine/subsystem/lwjgl/LwjglInput.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.lwjgl;

import org.lwjgl.LWJGLException;
import org.lwjgl.input.Keyboard;
import org.lwjgl.input.Mouse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.modes.GameState;
import org.terasology.input.InputSystem;
import org.terasology.input.lwjgl.LwjglKeyboardDevice;
import org.terasology.input.lwjgl.LwjglMouseDevice;

public class LwjglInput extends BaseLwjglSubsystem {

    private static final Logger logger = LoggerFactory.getLogger(LwjglInput.class);
    private Context context;

    @Override
    public void preInitialise(Context context) {
        super.preInitialise(context);
    }

    @Override
    public void initialise(Context context) {

    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
    }

    @Override
    public void postInitialise(Context context) {
        this.context = context;
        initControls();
        updateInputConfig();
        Mouse.setGrabbed(false);
    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }



    @Override
    public void postUpdate(GameState currentState, float delta) {
        currentState.handleInput(delta);
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
        Mouse.destroy();
        Keyboard.destroy();
    }

    private void initControls() {
        try {
            Keyboard.create();
            Keyboard.enableRepeatEvents(true);
            Mouse.create();
            InputSystem inputSystem = new InputSystem();
            context.put(InputSystem.class, inputSystem);
            inputSystem.setMouseDevice(new LwjglMouseDevice());
            inputSystem.setKeyboardDevice(new LwjglKeyboardDevice());
        } catch (LWJGLException e) {
            throw new RuntimeException("Could not initialize controls.", e);
        }
    }

    private void updateInputConfig() {
        Config config = context.get(Config.class);
        config.getInput().getBinds().updateForChangedMods(context);
        config.save();
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/engine/subsystem/lwjgl/LwjglTimer.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine.subsystem.lwjgl;

import org.terasology.assets.module.ModuleAwareAssetTypeManager;
import org.terasology.config.Config;
import org.terasology.context.Context;
import org.terasology.engine.ComponentSystemManager;
import org.terasology.engine.EngineTime;
import org.terasology.engine.Time;
import org.terasology.engine.internal.TimeLwjgl;
import org.terasology.engine.modes.GameState;

public class LwjglTimer extends BaseLwjglSubsystem {

    @Override
    public void preInitialise(Context context) {
        super.preInitialise(context);
        initTimer(context); // Dependent on LWJGL
    }

    @Override
    public void initialise(Context context) {

    }

    @Override
    public void registerCoreAssetTypes(ModuleAwareAssetTypeManager assetTypeManager) {
    }

    @Override
    public void postInitialise(Context context) {
    }

    @Override
    public void preUpdate(GameState currentState, float delta) {
    }

    @Override
    public void postUpdate(GameState currentState, float delta) {
    }

    @Override
    public void shutdown(Config config) {
    }

    @Override
    public void dispose() {
    }

    private void initTimer(Context context) {
        EngineTime time = new TimeLwjgl();
        context.put(Time.class, time);
    }

    @Override
    public void registerSystems(ComponentSystemManager componentSystemManager) {
    }

}


File: engine/src/main/java/org/terasology/logic/console/commands/CoreCommands.java
/*
 * Copyright 2015 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.logic.console.commands;

import org.terasology.asset.Assets;
import org.terasology.assets.management.AssetManager;
import org.terasology.engine.GameEngine;
import org.terasology.engine.TerasologyConstants;
import org.terasology.engine.TerasologyEngine;
import org.terasology.engine.modes.StateLoading;
import org.terasology.engine.modes.StateMainMenu;
import org.terasology.engine.paths.PathManager;
import org.terasology.entitySystem.entity.EntityManager;
import org.terasology.entitySystem.entity.EntityRef;
import org.terasology.entitySystem.entity.internal.EngineEntityManager;
import org.terasology.entitySystem.prefab.Prefab;
import org.terasology.entitySystem.prefab.PrefabManager;
import org.terasology.entitySystem.systems.BaseComponentSystem;
import org.terasology.entitySystem.systems.RegisterSystem;
import org.terasology.input.cameraTarget.CameraTargetSystem;
import org.terasology.logic.console.Console;
import org.terasology.logic.console.ConsoleColors;
import org.terasology.logic.console.Message;
import org.terasology.logic.console.commandSystem.ConsoleCommand;
import org.terasology.logic.console.commandSystem.annotations.Command;
import org.terasology.logic.console.commandSystem.annotations.CommandParam;
import org.terasology.logic.console.suggesters.CommandNameSuggester;
import org.terasology.logic.inventory.PickupBuilder;
import org.terasology.logic.location.LocationComponent;
import org.terasology.logic.permission.PermissionManager;
import org.terasology.math.Direction;
import org.terasology.math.geom.Quat4f;
import org.terasology.math.geom.Vector3f;
import org.terasology.naming.Name;
import org.terasology.network.JoinStatus;
import org.terasology.network.NetworkMode;
import org.terasology.network.NetworkSystem;
import org.terasology.persistence.WorldDumper;
import org.terasology.persistence.serializers.PrefabSerializer;
import org.terasology.registry.CoreRegistry;
import org.terasology.registry.In;
import org.terasology.rendering.FontColor;
import org.terasology.rendering.cameras.Camera;
import org.terasology.rendering.nui.NUIManager;
import org.terasology.rendering.nui.asset.UIElement;
import org.terasology.rendering.nui.layers.mainMenu.MessagePopup;
import org.terasology.rendering.nui.layers.mainMenu.WaitPopup;
import org.terasology.rendering.world.WorldRenderer;
import org.terasology.world.block.BlockManager;
import org.terasology.world.block.family.BlockFamily;
import org.terasology.world.block.items.BlockItemFactory;

import java.io.IOException;
import java.util.Collection;
import java.util.Optional;
import java.util.concurrent.Callable;

/**
 * @author Immortius
 */
@RegisterSystem
public class CoreCommands extends BaseComponentSystem {

    @In
    private EntityManager entityManager;

    @In
    private CameraTargetSystem cameraTargetSystem;

    @In
    private WorldRenderer worldRenderer;

    @In
    private PrefabManager prefabManager;

    @In
    private BlockManager blockManager;

    @In
    private Console console;

    private PickupBuilder pickupBuilder;

    @Override
    public void initialise() {
        pickupBuilder = new PickupBuilder(entityManager);
    }

    @Command(shortDescription = "Reloads a ui screen")
    public String reloadScreen(@CommandParam("ui") String ui) {
        Optional<UIElement> uiData = CoreRegistry.get(AssetManager.class).getAsset(ui, UIElement.class);
        if (uiData.isPresent()) {
            NUIManager nuiManager = CoreRegistry.get(NUIManager.class);
            boolean wasOpen = nuiManager.isOpen(uiData.get().getUrn());
            if (wasOpen) {
                nuiManager.closeScreen(uiData.get().getUrn());
            }

            if (wasOpen) {
                nuiManager.pushScreen(uiData.get());
            }
            return "Success";
        } else {
            return "Unable to resolve ui '" + ui + "'";
        }
    }

    @Command(shortDescription = "Toggles Fullscreen Mode", requiredPermission = PermissionManager.NO_PERMISSION)
    public String fullscreen() {
        TerasologyEngine te = (TerasologyEngine) CoreRegistry.get(GameEngine.class);

        te.setFullscreen(!te.isFullscreen());

        if (te.isFullscreen()) {
            return "Switched to fullscreen mode";
        } else {
            return "Switched to windowed mode";
        }

    }

    @Command(shortDescription = "Removes all entities of the given prefab", runOnServer = true)
    public void destroyEntitiesUsingPrefab(@CommandParam("prefabName") String prefabName) {
        Prefab prefab = entityManager.getPrefabManager().getPrefab(prefabName);
        if (prefab != null) {
            for (EntityRef entity : entityManager.getAllEntities()) {
                if (prefab.equals(entity.getParentPrefab())) {
                    entity.destroy();
                }
            }
        }
    }

    @Command(shortDescription = "Exits the game", requiredPermission = PermissionManager.NO_PERMISSION)
    public void exit() {
        CoreRegistry.get(GameEngine.class).shutdown();
    }

    @Command(shortDescription = "Join a game", requiredPermission = PermissionManager.NO_PERMISSION)
    public void join(@CommandParam("address") final String address, @CommandParam(value = "port", required = false) Integer portParam) {
        final int port = portParam != null ? portParam : TerasologyConstants.DEFAULT_PORT;

        Callable<JoinStatus> operation = new Callable<JoinStatus>() {

            @Override
            public JoinStatus call() throws InterruptedException {
                NetworkSystem networkSystem = CoreRegistry.get(NetworkSystem.class);
                JoinStatus joinStatus = networkSystem.join(address, port);
                return joinStatus;
            }
        };

        final NUIManager manager = CoreRegistry.get(NUIManager.class);
        final WaitPopup<JoinStatus> popup = manager.pushScreen(WaitPopup.ASSET_URI, WaitPopup.class);
        popup.setMessage("Join Game", "Connecting to '" + address + ":" + port + "' - please wait ...");
        popup.onSuccess(result -> {
                GameEngine engine = CoreRegistry.get(GameEngine.class);
                if (result.getStatus() != JoinStatus.Status.FAILED) {
                    engine.changeState(new StateLoading(result));
                } else {
                    MessagePopup screen = manager.pushScreen(MessagePopup.ASSET_URI, MessagePopup.class);
                    screen.setMessage("Failed to Join", "Could not connect to server - " + result.getErrorMessage());
                }
            });
        popup.startOperation(operation, true);
    }

    @Command(shortDescription = "Leaves the current game and returns to main menu",
            requiredPermission = PermissionManager.NO_PERMISSION)
    public String leave() {
        NetworkSystem networkSystem = CoreRegistry.get(NetworkSystem.class);
        if (networkSystem.getMode() != NetworkMode.NONE) {
            CoreRegistry.get(GameEngine.class).changeState(new StateMainMenu());
            return "Leaving..";
        } else {
            return "Not connected";
        }
    }

    @Command(shortDescription = "Writes out information on all entities to a text file for debugging",
            helpText = "Writes entity information out into a file named \"entityDump.txt\".")
    public void dumpEntities() throws IOException {
        EngineEntityManager engineEntityManager = (EngineEntityManager) entityManager;
        PrefabSerializer prefabSerializer = new PrefabSerializer(engineEntityManager.getComponentLibrary(), engineEntityManager.getTypeSerializerLibrary());
        WorldDumper worldDumper = new WorldDumper(engineEntityManager, prefabSerializer);
        worldDumper.save(PathManager.getInstance().getHomePath().resolve("entityDump.txt"));
    }

    // TODO: Fix this up for multiplayer (cannot at the moment due to the use of the camera)
    @Command(shortDescription = "Spawns an instance of a prefab in the world")
    public String spawnPrefab(@CommandParam("prefabId") String prefabName) {
        Camera camera = worldRenderer.getActiveCamera();
        Vector3f spawnPos = camera.getPosition();
        Vector3f offset = new Vector3f(camera.getViewingDirection());
        offset.scale(2);
        spawnPos.add(offset);
        Vector3f dir = new Vector3f(camera.getViewingDirection());
        dir.y = 0;
        if (dir.lengthSquared() > 0.001f) {
            dir.normalize();
        } else {
            dir.set(Direction.FORWARD.getVector3f());
        }
        Quat4f rotation = Quat4f.shortestArcQuat(Direction.FORWARD.getVector3f(), dir);

        Optional<Prefab> prefab = Assets.getPrefab(prefabName);
        if (prefab.isPresent() && prefab.get().getComponent(LocationComponent.class) != null) {
            entityManager.create(prefab.get(), spawnPos, rotation);
            return "Done";
        } else if (!prefab.isPresent()) {
            return "Unknown prefab";
        } else {
            return "Prefab cannot be spawned (no location component)";
        }
    }

    // TODO: Fix this up for multiplayer (cannot at the moment due to the use of the camera), also applied required
    // TODO: permission
    @Command(shortDescription = "Spawns a block in front of the player", helpText = "Spawns the specified block as a " +
            "item in front of the player. You can simply pick it up.")
    public String spawnBlock(@CommandParam("blockName") String blockName) {
        Camera camera = worldRenderer.getActiveCamera();
        Vector3f spawnPos = camera.getPosition();
        Vector3f offset = camera.getViewingDirection();
        offset.scale(3);
        spawnPos.add(offset);

        BlockFamily block = blockManager.getBlockFamily(blockName);
        if (block == null) {
            return "";
        }

        BlockItemFactory blockItemFactory = new BlockItemFactory(entityManager);
        EntityRef blockItem = blockItemFactory.newInstance(block);

        pickupBuilder.createPickupFor(blockItem, spawnPos, 60);
        return "Spawned block.";
    }

    @Command(shortDescription = "Prints out short descriptions for all available commands, or a longer help text if a command is provided.",
            requiredPermission = PermissionManager.NO_PERMISSION)
    public String help(@CommandParam(value = "command", required = false, suggester = CommandNameSuggester.class) Name commandName) {
        if (commandName == null) {
            StringBuilder msg = new StringBuilder();
            Collection<ConsoleCommand> commands = console.getCommands();

            for (ConsoleCommand cmd : commands) {
                if (!msg.toString().isEmpty()) {
                    msg.append(Message.NEW_LINE);
                }

                msg.append(FontColor.getColored(cmd.getUsage(), ConsoleColors.COMMAND));
                msg.append(" - ");
                msg.append(cmd.getDescription());
            }

            return msg.toString();
        } else {
            ConsoleCommand cmd = console.getCommand(commandName);
            if (cmd == null) {
                return "No help available for command '" + commandName + "'. Unknown command.";
            } else {
                StringBuilder msg = new StringBuilder();

                msg.append("=====================================================================================================================");
                msg.append(Message.NEW_LINE);
                msg.append(cmd.getUsage());
                msg.append(Message.NEW_LINE);
                msg.append("=====================================================================================================================");
                msg.append(Message.NEW_LINE);
                if (!cmd.getHelpText().isEmpty()) {
                    msg.append(cmd.getHelpText());
                    msg.append(Message.NEW_LINE);
                    msg.append("=====================================================================================================================");
                    msg.append(Message.NEW_LINE);
                } else if (!cmd.getDescription().isEmpty()) {
                    msg.append(cmd.getDescription());
                    msg.append(Message.NEW_LINE);
                    msg.append("=====================================================================================================================");
                    msg.append(Message.NEW_LINE);
                }

                return msg.toString();
            }
        }
    }
}


File: engine/src/main/java/org/terasology/rendering/opengl/LwjglRenderingProcess.java
/*
 * Copyright 2013 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.rendering.opengl;

import com.google.common.collect.Maps;
import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.Display;
import org.lwjgl.opengl.GL11;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.terasology.config.Config;
import org.terasology.config.RenderingConfig;
import org.terasology.engine.GameEngine;
import org.terasology.engine.paths.PathManager;
import org.terasology.engine.subsystem.ThreadManager;
import org.terasology.math.TeraMath;
import org.terasology.monitoring.PerformanceMonitor;
import org.terasology.registry.CoreRegistry;
import org.terasology.rendering.oculusVr.OculusVrHelper;
import org.terasology.rendering.opengl.FBO.Dimensions;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.BufferedOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;

import static org.lwjgl.opengl.EXTFramebufferObject.glDeleteFramebuffersEXT;
import static org.lwjgl.opengl.EXTFramebufferObject.glDeleteRenderbuffersEXT;

/**
 * The Default Rendering Process class.
 *
 * @author Benjamin Glatzel
 */
public class LwjglRenderingProcess {

    private static final Logger logger = LoggerFactory.getLogger(LwjglRenderingProcess.class);

    private PBO readBackPBOFront;
    private PBO readBackPBOBack;
    private PBO readBackPBOCurrent;

    // I could have named them fullResolution, halfResolution and so on. But halfScale is actually
    // -both- fullScale's dimensions halved, leading to -a quarter- of its resolution. Following
    // this logic one32thScale would have to be named one1024thResolution and the otherwise
    // straightforward connection between variable names and dimensions would have been lost. -- manu3d
    private Dimensions fullScale;
    private Dimensions halfScale;
    private Dimensions quarterScale;
    private Dimensions one8thScale;
    private Dimensions one16thScale;
    private Dimensions one32thScale;

    private int overwriteRtWidth;
    private int overwriteRtHeight;

    private String currentlyBoundFboName = "";
    private FBO currentlyBoundFbo;
    //private int currentlyBoundTextureId = -1;

    /* VARIOUS */
    private boolean isTakingScreenshot;

    // Note: this assumes that the settings in the configs might change at runtime,
    // but the config objects will not. At some point this might change, i.e. implementing presets.
    private Config config = CoreRegistry.get(Config.class);
    private RenderingConfig renderingConfig = config.getRendering();

    private Map<String, FBO> fboLookup = Maps.newHashMap();

    private GraphicState graphicState;
    private PostProcessor postProcessor;

    public LwjglRenderingProcess() {

    }

    public void initialize() {
        createOrUpdateFullscreenFbos();

        // Note: the FBObuilder takes care of registering thew new FBOs on fboLookup.
        new FBObuilder("scene16", 16, 16, FBO.Type.DEFAULT).build();
        new FBObuilder("scene8",   8,  8, FBO.Type.DEFAULT).build();
        new FBObuilder("scene4",   4,  4, FBO.Type.DEFAULT).build();
        new FBObuilder("scene2",   2,  2, FBO.Type.DEFAULT).build();
        new FBObuilder("scene1",   1,  1, FBO.Type.DEFAULT).build();

        postProcessor.obtainStaticFBOs();

        readBackPBOFront = new PBO(1, 1);
        readBackPBOBack = new PBO(1, 1);
        readBackPBOCurrent = readBackPBOFront;
    }

    public void setGraphicState(GraphicState graphicState) {
        this.graphicState = graphicState;
    }

    public void setPostProcessor(PostProcessor postProcessor) {
        this.postProcessor = postProcessor;
    }

    /**
     * Creates the scene FBOs and updates them according to the size of the viewport. The current size
     * provided by the display class is only used if the parameters overwriteRTWidth and overwriteRTHeight are set
     * to zero.
     */
    public void createOrUpdateFullscreenFbos() {

        if (overwriteRtWidth == 0) {
            fullScale = new Dimensions(Display.getWidth(), Display.getHeight());
        } else {
            fullScale = new Dimensions(overwriteRtWidth, overwriteRtHeight);
            if (renderingConfig.isOculusVrSupport()) {
                fullScale.multiplySelfBy(OculusVrHelper.getScaleFactor());
            }
        }

        fullScale.multiplySelfBy(renderingConfig.getFboScale() / 100f);

        halfScale    = fullScale.dividedBy(2);   // quarter resolution
        quarterScale = fullScale.dividedBy(4);   // one 16th resolution
        one8thScale  = fullScale.dividedBy(8);   // one 64th resolution
        one16thScale = fullScale.dividedBy(16);  // one 256th resolution
        one32thScale = fullScale.dividedBy(32);  // one 1024th resolution

        FBO scene = fboLookup.get("sceneOpaque");
        final boolean recreate = scene == null || (scene.dimensions().areDifferentFrom(fullScale));

        if (!recreate) {
            return;
        }

        // Note: the FBObuilder takes care of registering thew new FBOs on fboLookup.
        int shadowMapResolution = renderingConfig.getShadowMapResolution();
        FBO sceneShadowMap =
                new FBObuilder("sceneShadowMap", shadowMapResolution, shadowMapResolution, FBO.Type.NO_COLOR).useDepthBuffer().build();
        graphicState.setSceneShadowMap(sceneShadowMap);

        // buffers for the initial renderings
        FBO sceneOpaque =
                new FBObuilder("sceneOpaque", fullScale, FBO.Type.HDR).useDepthBuffer().useNormalBuffer().useLightBuffer().useStencilBuffer().build();
        new FBObuilder("sceneOpaquePingPong", fullScale, FBO.Type.HDR).useDepthBuffer().useNormalBuffer().useLightBuffer().useStencilBuffer().build();

        new FBObuilder("sceneSkyBand0", one16thScale, FBO.Type.DEFAULT).build();
        new FBObuilder("sceneSkyBand1", one32thScale, FBO.Type.DEFAULT).build();

        FBO sceneReflectiveRefractive = new FBObuilder("sceneReflectiveRefractive", fullScale, FBO.Type.HDR).useNormalBuffer().build();
        sceneOpaque.attachDepthBufferTo(sceneReflectiveRefractive);

        new FBObuilder("sceneReflected",  halfScale,    FBO.Type.DEFAULT).useDepthBuffer().build();

        // buffers for the prePost-Processing composite
        new FBObuilder("outline",         fullScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("ssao",            fullScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("ssaoBlurred",     fullScale,    FBO.Type.DEFAULT).build();

        // buffers for the Initial Post-Processing
        new FBObuilder("lightShafts",     halfScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("initialPost",     fullScale,    FBO.Type.HDR).build();
        new FBObuilder("sceneToneMapped", fullScale,    FBO.Type.HDR).build();

        new FBObuilder("sceneHighPass",   fullScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("sceneBloom0",     halfScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("sceneBloom1",     quarterScale, FBO.Type.DEFAULT).build();
        new FBObuilder("sceneBloom2",     one8thScale,  FBO.Type.DEFAULT).build();

        new FBObuilder("sceneBlur0",      halfScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("sceneBlur1",      halfScale,    FBO.Type.DEFAULT).build();

        // buffers for the Final Post-Processing
        new FBObuilder("ocUndistorted",   fullScale,    FBO.Type.DEFAULT).build();
        new FBObuilder("sceneFinal",      fullScale,    FBO.Type.DEFAULT).build();

        graphicState.refreshDynamicFBOs();
        postProcessor.refreshDynamicFBOs();
    }

    public void deleteFBO(String title) {
        if (fboLookup.containsKey(title)) {
            FBO fbo = fboLookup.get(title);

            glDeleteFramebuffersEXT(fbo.fboId);
            glDeleteRenderbuffersEXT(fbo.depthStencilRboId);
            GL11.glDeleteTextures(fbo.normalsBufferTextureId);
            GL11.glDeleteTextures(fbo.depthStencilTextureId);
            GL11.glDeleteTextures(fbo.colorBufferTextureId);
        }
    }

    public void takeScreenshot() {
        isTakingScreenshot = true;

        overwriteRtWidth = renderingConfig.getScreenshotSize().getWidth(Display.getWidth());
        overwriteRtHeight = renderingConfig.getScreenshotSize().getHeight(Display.getHeight());

        createOrUpdateFullscreenFbos();
    }

    public void saveScreenshot() {
        if (!isTakingScreenshot) {
            return;
        }

        final FBO fboSceneFinal = getFBO("sceneFinal");

        if (fboSceneFinal == null) {
            return;
        }

        final ByteBuffer buffer = BufferUtils.createByteBuffer(fboSceneFinal.width() * fboSceneFinal.height() * 4);

        fboSceneFinal.bindTexture();
        GL11.glGetTexImage(GL11.GL_TEXTURE_2D, 0, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, buffer);
        fboSceneFinal.unbindTexture();

        Runnable task = new Runnable() {
            @Override
            public void run() {
                SimpleDateFormat sdf = new SimpleDateFormat("yyMMddHHmmss");

                final String format = renderingConfig.getScreenshotFormat().toString();
                final String fileName = "Terasology-" + sdf.format(new Date()) + "-" + fboSceneFinal.width() + "x" + fboSceneFinal.height() + "." + format;
                Path path = PathManager.getInstance().getScreenshotPath().resolve(fileName);
                BufferedImage image = new BufferedImage(fboSceneFinal.width(), fboSceneFinal.height(), BufferedImage.TYPE_INT_RGB);

                for (int x = 0; x < fboSceneFinal.width(); x++) {
                    for (int y = 0; y < fboSceneFinal.height(); y++) {
                        int i = (x + fboSceneFinal.width() * y) * 4;
                        int r = buffer.get(i) & 0xFF;
                        int g = buffer.get(i + 1) & 0xFF;
                        int b = buffer.get(i + 2) & 0xFF;
                        image.setRGB(x, fboSceneFinal.height() - (y + 1), (0xFF << 24) | (r << 16) | (g << 8) | b);
                    }
                }

                try (OutputStream out = new BufferedOutputStream(Files.newOutputStream(path))) {
                    ImageIO.write(image, format, out);
                    logger.info("Screenshot '" + fileName + "' saved! ");
                } catch (IOException e) {
                    logger.warn("Failed to save screenshot!", e);
                }
            }
        };

        CoreRegistry.get(ThreadManager.class).submitTask("Write screenshot", task);

        isTakingScreenshot = false;
        overwriteRtWidth = 0;
        overwriteRtHeight = 0;

        createOrUpdateFullscreenFbos();
    }

    public FBO getFBO(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo == null) {
            logger.error("Failed to retrieve FBO '" + title + "'!");
        }

        return fbo;
    }

    public boolean bindFbo(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo != null) {
            fbo.bind();
            currentlyBoundFboName = title;
            return true;
        }

        logger.error("Failed to bind FBO since the requested FBO could not be found!");
        return false;
    }

    public boolean unbindFbo(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo != null) {
            fbo.unbind();
            currentlyBoundFboName = "";
            return true;
        }

        logger.error("Failed to unbind FBO since the requested FBO could not be found!");
        return false;
    }

    public boolean bindFboColorTexture(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo != null) {
            fbo.bindTexture();
            return true;
        }

        logger.error("Failed to bind FBO color texture since the requested " + title + " FBO could not be found!");
        return false;
    }

    public boolean bindFboDepthTexture(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo != null) {
            fbo.bindDepthTexture();
            return true;
        }

        logger.error("Failed to bind FBO depth texture since the requested " + title + " FBO could not be found!");
        return false;
    }

    public boolean bindFboNormalsTexture(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo != null) {
            fbo.bindNormalsTexture();
            return true;
        }

        logger.error("Failed to bind FBO normals texture since the requested " + title + " FBO could not be found!");
        return false;
    }

    public boolean bindFboLightBufferTexture(String title) {
        FBO fbo = fboLookup.get(title);

        if (fbo != null) {
            fbo.bindLightBufferTexture();
            return true;
        }

        logger.error("Failed to bind FBO light buffer texture since the requested " + title + " FBO could not be found!");
        return false;
    }

    public void flipPingPongFbo(String title) {
        FBO fbo1 = getFBO(title);
        FBO fbo2 = getFBO(title + "PingPong");

        if (fbo1 == null || fbo2 == null) {
            return;
        }

        fboLookup.put(title, fbo2);
        fboLookup.put(title + "PingPong", fbo1);
    }

    public void swapSceneOpaqueFBOs() {
        FBO currentSceneOpaquePingPong = fboLookup.get("sceneOpaquePingPong");
        fboLookup.put("sceneOpaquePingPong", fboLookup.get("sceneOpaque"));
        fboLookup.put("sceneOpaque", currentSceneOpaquePingPong);

        graphicState.setSceneOpaqueFBO(currentSceneOpaquePingPong);
        postProcessor.refreshSceneOpaqueFBOs();
    }

    public void swapReadbackPBOs() {
        if (readBackPBOCurrent == readBackPBOFront) {
            readBackPBOCurrent = readBackPBOBack;
        } else {
            readBackPBOCurrent = readBackPBOFront;
        }
    }

    public PBO getCurrentReadbackPBO() {
        return readBackPBOCurrent;
    }

    public boolean isTakingScreenshot() {
        return isTakingScreenshot;
    }

    public boolean isNotTakingScreenshot() {
        return !isTakingScreenshot;
    }

    /**
     * Builder class to simplify the syntax creating an FBO.
     * <p>
     * Once the desired characteristics of the FBO are set via the Builder's constructor and its
     * use*Buffer() methods, the build() method can be called for the actual FBO to be generated,
     * alongside the underlying FrameBuffer and its attachments on the GPU.
     * <p>
     * The new FBO is automatically registered with the LwjglRenderingProcess, overwriting any
     * existing FBO with the same title.
     */
    public class FBObuilder {

        private FBO generatedFBO;

        private String title;
        private FBO.Dimensions dimensions;
        private FBO.Type type;

        private boolean useDepthBuffer;
        private boolean useNormalBuffer;
        private boolean useLightBuffer;
        private boolean useStencilBuffer;

        /**
         * Constructs an FBO builder capable of building the two most basic FBOs:
         * an FBO with no attachments or one with a single color buffer attached to it.
         * <p>
         * To attach additional buffers, see the use*Buffer() methods.
         * <p>
         * Example: FBO basicFBO = new FBObuilder("basic", new Dimensions(1920, 1080), Type.DEFAULT).build();
         *
         * @param title A string identifier, the title is used to later manipulate the FBO through
         *              methods such as LwjglRenderingProcess.getFBO(title) and LwjglRenderingProcess.bindFBO(title).
         * @param dimensions A Dimensions object providing width and height information.
         * @param type Type.DEFAULT will result in a 32 bit color buffer attached to the FBO. (GL_RGBA, GL11.GL_UNSIGNED_BYTE, GL_LINEAR)
         *             Type.HDR will result in a 64 bit color buffer attached to the FBO. (GL_RGBA, GL_HALF_FLOAT_ARB, GL_LINEAR)
         *             Type.NO_COLOR will result in -no- color buffer attached to the FBO
         *             (WARNING: this could result in an FBO with Status.DISPOSED - see FBO.getStatus()).
         */
        public FBObuilder(String title, FBO.Dimensions dimensions, FBO.Type type) {
            this.title = title;
            this.dimensions = dimensions;
            this.type = type;
        }

        /**
         * Same as the previous FBObuilder constructor, but taking in input
         * explicit, integer width and height instead of a Dimensions object.
         */
        public FBObuilder(String title, int width, int height, FBO.Type type) {
            this(title,  new FBO.Dimensions(width, height), type);
        }

/*
 *  * @param useDepthBuffer If true the FBO will have a 24 bit depth buffer attached to it. (GL_DEPTH_COMPONENT24, GL_UNSIGNED_INT, GL_NEAREST)
    * @param useNormalBuffer If true the FBO will have a 32 bit normals buffer attached to it. (GL_RGBA, GL_UNSIGNED_BYTE, GL_LINEAR)
    * @param useLightBuffer If true the FBO will have 32/64 bit light buffer attached to it, depending if Type is DEFAULT/HDR.
*                       (GL_RGBA/GL_RGBA16F_ARB, GL_UNSIGNED_BYTE/GL_HALF_FLOAT_ARB, GL_LINEAR)
    * @param useStencilBuffer If true the depth buffer will also have an 8 bit Stencil buffer associated with it.
    *                         (GL_DEPTH24_STENCIL8_EXT, GL_UNSIGNED_INT_24_8_EXT, GL_NEAREST)
                *                         */

        /**
         * Sets the builder to generate, allocate and attach a 24 bit depth buffer to the FrameBuffer to be built.
         * If useStencilBuffer() is also used, an 8 bit stencil buffer will also be associated with the depth buffer.
         * For details on the specific characteristics of the buffers, see the FBO.create() method.
         *
         * @return The calling instance, to chain calls, i.e.: new FBObuilder(...).useDepthBuffer().build();
         */
        public FBObuilder useDepthBuffer() {
            useDepthBuffer = true;
            return this;
        }

        /**
         * Sets the builder to generate, allocate and attach a normals buffer to the FrameBuffer to be built.
         * For details on the specific characteristics of the buffer, see the FBO.create() method.
         *
         * @return The calling instance, to chain calls, i.e.: new FBObuilder(...).useNormalsBuffer().build();
         */
        public FBObuilder useNormalBuffer() {
            useNormalBuffer = true;
            return this;
        }

        /**
         * Sets the builder to generate, allocate and attach a light buffer to the FrameBuffer to be built.
         * Be aware that the number of bits per channel for this buffer changes with the set FBO.Type.
         * For details see the FBO.create() method.
         *
         * @return The calling instance, to chain calls, i.e.: new FBObuilder(...).useLightBuffer().build();
         */
        public FBObuilder useLightBuffer() {
            useLightBuffer = true;
            return this;
        }

        /**
         * -IF- the builder has been set to generate a depth buffer, using this method sets the builder to
         * generate a depth buffer inclusive of stencil buffer, with the following characteristics:
         * internal format GL_DEPTH24_STENCIL8_EXT, data type GL_UNSIGNED_INT_24_8_EXT and filtering GL_NEAREST.
         *
         * @return The calling instance of FBObuilder, to chain calls,
         *         i.e.: new FBObuilder(...).useDepthBuffer().useStencilBuffer().build();
         */
        public FBObuilder useStencilBuffer() {
            useStencilBuffer = true;
            return this;
        }

        /**
         * Given information set through the constructor and the use*Buffer() methods, builds and returns
         * an FBO instance, inclusive the underlying OpenGL FrameBuffer and any requested attachments.
         * <p>
         * The FBO is also automatically registered with the LwjglRenderingProcess through its title string.
         * This allows its retrieval and binding through methods such as getFBO(String title) and
         * bindFBO(String title). If another FBO is registered with the same title, it is disposed and
         * the new FBO registered in its place.
         * <p>
         * This method is effectively mono-use: calling it more than once will return the exact same FBO
         * returned the first time. To build a new FBO with identical or different characteristics it's
         * necessary to instantiate a new builder.
         *
         * @return An FBO. Make sure to check it with FBO.getStatus() before using it.
         */
        public FBO build() {
            if (generatedFBO != null) {
                return generatedFBO;
            }

            FBO oldFBO = fboLookup.get(title);
            if (oldFBO != null) {
                oldFBO.dispose();
                fboLookup.remove(title);
                logger.warn("FBO " + title + " has been overwritten. Ideally it would have been deleted first.");
            }

            generatedFBO = FBO.create(title, dimensions, type, useDepthBuffer, useNormalBuffer, useLightBuffer, useStencilBuffer);
            handleIncompleteAndUnexpectedStatus(generatedFBO);
            fboLookup.put(title, generatedFBO);
            return generatedFBO;
        }

        private void handleIncompleteAndUnexpectedStatus(FBO fbo) {
            // At this stage it's unclear what should be done in this circumstances as I (manu3d) do not know what
            // the effects of using an incomplete FrameBuffer are. Throw an exception? Live with visual artifacts?
            if (fbo.getStatus() == FBO.Status.INCOMPLETE) {
                logger.error("FBO " + title + " is incomplete. Look earlier in the log for details.");
            } else if (fbo.getStatus() == FBO.Status.UNEXPECTED) {
                logger.error("FBO " + title + " has generated an unexpected status code. Look earlier in the log for details.");
            }
        }
    }
}



File: facades/PC/src/main/java/org/terasology/engine/Terasology.java
/*
 * Copyright 2015 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.terasology.engine;

import com.google.common.base.Joiner;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.Lists;
import org.terasology.config.Config;
import org.terasology.crashreporter.CrashReporter;
import org.terasology.engine.modes.StateLoading;
import org.terasology.engine.modes.StateMainMenu;
import org.terasology.engine.paths.PathManager;
import org.terasology.engine.splash.SplashScreen;
import org.terasology.engine.subsystem.EngineSubsystem;
import org.terasology.engine.subsystem.ThreadManager;
import org.terasology.engine.subsystem.headless.HeadlessAudio;
import org.terasology.engine.subsystem.headless.HeadlessGraphics;
import org.terasology.engine.subsystem.headless.HeadlessInput;
import org.terasology.engine.subsystem.headless.HeadlessTimer;
import org.terasology.engine.subsystem.headless.mode.HeadlessStateChangeListener;
import org.terasology.engine.subsystem.headless.mode.StateHeadlessSetup;
import org.terasology.engine.subsystem.lwjgl.LwjglAudio;
import org.terasology.engine.subsystem.lwjgl.LwjglGraphics;
import org.terasology.engine.subsystem.lwjgl.LwjglInput;
import org.terasology.engine.subsystem.lwjgl.LwjglTimer;
import org.terasology.game.GameManifest;
import org.terasology.network.NetworkMode;
import org.terasology.rendering.nui.layers.mainMenu.savedGames.GameInfo;
import org.terasology.rendering.nui.layers.mainMenu.savedGames.GameProvider;

import java.awt.*;
import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collection;
import java.util.List;

/**
 * Class providing the main() method for launching Terasology as a PC app.
 * <br><br>
 * Through the following launch arguments default locations to store logs and
 * game saves can be overridden, by using the current directory or a specified
 * one as the home directory. Furthermore, Terasology can be launched headless,
 * to save resources while acting as a server or to run in an environment with
 * no graphics, audio or input support. Additional arguments are available to
 * reload the latest game on startup and to disable crash reporting.
 * <br><br>
 * Available launch arguments:
 * <br><br>
 * <table summary="Launch arguments">
 * <tbody>
 * <tr><td>-homedir</td><td>Use the current directory as the home directory.</td></tr>
 * <tr><td>-homedir=path</td><td>Use the specified path as the home directory.</td></tr>
 * <tr><td>-headless</td><td>Start headless.</td></tr>
 * <tr><td>-loadlastgame</td><td>Load the latest game on startup.</td></tr>
 * <tr><td>-noSaveGames</td><td>Disable writing of save games.</td></tr>
 * <tr><td>-noCrashReport</td><td>Disable crash reporting</td></tr>
 * <tr><td>-serverPort=xxxxx</td><td>Change the server port.</td></tr>
 * </tbody>
 * </table>
 * <br><br>
 * When used via command line an usage help and some examples can be obtained via:
 * <br><br>
 * terasology -help    or    terasology /?
 * <br><br>
 *
 * @author Benjamin Glatzel
 * @author Anton Kireev
 * @author and many others
 */

public final class Terasology {

    private static final String[] PRINT_USAGE_FLAGS = {"--help", "-help", "/help", "-h", "/h", "-?", "/?"};
    private static final String USE_CURRENT_DIR_AS_HOME = "-homedir";
    private static final String USE_SPECIFIED_DIR_AS_HOME = "-homedir=";
    private static final String START_HEADLESS = "-headless";
    private static final String LOAD_LAST_GAME = "-loadlastgame";
    private static final String NO_CRASH_REPORT = "-noCrashReport";
    private static final String NO_SAVE_GAMES = "-noSaveGames";
    private static final String NO_SOUND = "-noSound";
    private static final String SERVER_PORT = "-serverPort=";

    private static boolean isHeadless;
    private static boolean crashReportEnabled = true;
    private static boolean writeSaveGamesEnabled = true;
    private static boolean soundEnabled = true;
    private static boolean loadLastGame;
    private static String serverPort = null;

    private Terasology() {
    }

    public static void main(String[] args) {

        // To have the splash screen in your favorite IDE add
        //
        //   eclipse:  -splash:src/main/resources/splash.jpg (the PC facade root folder is the working dir.)
        //   IntelliJ: -splash:facades/PC/src/main/resources/splash.jpg (root project is the working dir.)
        //
        // as JVM argument (not program argument!)

        SplashScreen.getInstance().post("Java Runtime " + System.getProperty("java.version") + " loaded");

        handlePrintUsageRequest(args);
        handleLaunchArguments(args);

        setupLogging();

        try {
            TerasologyEngine engine = new TerasologyEngine(createSubsystemList());
            engine.subscribe(newStatus -> {
                if (newStatus == StandardGameStatus.RUNNING) {
                    SplashScreen.getInstance().close();
                } else {
                    SplashScreen.getInstance().post(newStatus.getDescription());
                }
            });
            Config config = engine.getFromEngineContext(Config.class);

            if (!writeSaveGamesEnabled) {
                config.getTransients().setWriteSaveGamesEnabled(writeSaveGamesEnabled);
            }

            if (serverPort != null) {
                config.getTransients().setServerPort(Integer.parseInt(serverPort));
            }

            if (isHeadless) {
                engine.subscribeToStateChange(new HeadlessStateChangeListener(engine));
                engine.run(new StateHeadlessSetup());
            } else {
                if (loadLastGame) {
                    engine.getFromEngineContext(ThreadManager.class).submitTask("loadGame", new Runnable() {
                        @Override
                        public void run() {
                            GameManifest gameManifest = getLatestGameManifest();
                            if (gameManifest != null) {
                                engine.changeState(new StateLoading(gameManifest, NetworkMode.NONE));
                            }
                        }
                    });
                }

                engine.run(new StateMainMenu());
            }
        } catch (Throwable e) {
            // also catch Errors such as UnsatisfiedLink, NoSuchMethodError, etc.
            SplashScreen.getInstance().close();
            reportException(e);
        }
    }

    private static void setupLogging() {
        Path path = PathManager.getInstance().getLogPath();
        if (path == null) {
            path = Paths.get("logs");
        }

        LoggingContext.initialize(path);
    }

    private static void handlePrintUsageRequest(String[] args) {
        for (String arg : args) {
            for (String usageArg : PRINT_USAGE_FLAGS) {
                if (usageArg.equals(arg.toLowerCase())) {
                    printUsageAndExit();
                }
            }
        }
    }

    private static void printUsageAndExit() {

        String printUsageFlags = Joiner.on("|").join(PRINT_USAGE_FLAGS);

        List<String> opts = ImmutableList.of(
                printUsageFlags,
                USE_CURRENT_DIR_AS_HOME + "|" + USE_SPECIFIED_DIR_AS_HOME + "<path>",
                START_HEADLESS,
                LOAD_LAST_GAME,
                NO_CRASH_REPORT,
                NO_SAVE_GAMES,
                NO_SOUND,
                SERVER_PORT + "<port>");

        StringBuilder optText = new StringBuilder();

        for (String opt : opts) {
            optText.append(" [" + opt + "]");
        }

        System.out.println("Usage:");
        System.out.println();
        System.out.println("    terasology" + optText.toString());
        System.out.println();
        System.out.println("By default Terasology saves data such as game saves and logs into subfolders of a platform-specific \"home directory\".");
        System.out.println("Saving can be explicitly disabled using the \"" + NO_SAVE_GAMES + "\" flag.");
        System.out.println("Optionally, the user can override the default by using one of the following launch arguments:");
        System.out.println();
        System.out.println("    " + USE_CURRENT_DIR_AS_HOME + "        Use the current directory as the home directory.");
        System.out.println("    " + USE_SPECIFIED_DIR_AS_HOME + "<path> Use the specified directory as the home directory.");
        System.out.println();
        System.out.println("It is also possible to start Terasology in headless mode (no graphics), i.e. to act as a server.");
        System.out.println("For this purpose use the " + START_HEADLESS + " launch argument.");
        System.out.println();
        System.out.println("To automatically load the latest game on startup,");
        System.out.println("use the " + LOAD_LAST_GAME + " launch argument.");
        System.out.println();
        System.out.println("By default Crash Reporting is enabled.");
        System.out.println("To disable this feature use the " + NO_CRASH_REPORT + " launch argument.");
        System.out.println();
        System.out.println("To disable sound use the " + NO_SOUND + " launch argument (default in headless mode).");
        System.out.println();
        System.out.println("To change the port the server is hosted on use the " + SERVER_PORT + " launch argument.");
        System.out.println();
        System.out.println("Examples:");
        System.out.println();
        System.out.println("    Use the current directory as the home directory:");
        System.out.println("    terasology " + USE_CURRENT_DIR_AS_HOME);
        System.out.println();
        System.out.println("    Use \"myPath\" as the home directory:");
        System.out.println("    terasology " + USE_SPECIFIED_DIR_AS_HOME + "myPath");
        System.out.println();
        System.out.println("    Start terasology in headless mode (no graphics) and enforce using the default port:");
        System.out.println("    terasology " + START_HEADLESS + " " + SERVER_PORT + TerasologyConstants.DEFAULT_PORT);
        System.out.println();
        System.out.println("    Load the latest game on startup and disable crash reporting");
        System.out.println("    terasology " + LOAD_LAST_GAME + " " + NO_CRASH_REPORT);
        System.out.println();
        System.out.println("    Don't start Terasology, just print this help:");
        System.out.println("    terasology " + PRINT_USAGE_FLAGS[1]);
        System.out.println();

        System.exit(0);
    }

    private static void handleLaunchArguments(String[] args) {

        Path homePath = null;

        for (String arg : args) {
            boolean recognized = true;

            if (arg.startsWith(USE_SPECIFIED_DIR_AS_HOME)) {
                homePath = Paths.get(arg.substring(USE_SPECIFIED_DIR_AS_HOME.length()));
            } else if (arg.equals(USE_CURRENT_DIR_AS_HOME)) {
                homePath = Paths.get("");
            } else if (arg.equals(START_HEADLESS)) {
                isHeadless = true;
                crashReportEnabled = false;
            } else if (arg.equals(NO_SAVE_GAMES)) {
                writeSaveGamesEnabled = false;
            } else if (arg.equals(NO_CRASH_REPORT)) {
                crashReportEnabled = false;
            } else if (arg.equals(NO_SOUND)) {
                soundEnabled = false;
            } else if (arg.equals(LOAD_LAST_GAME)) {
                loadLastGame = true;
            } else if (arg.startsWith(SERVER_PORT)) {
                serverPort = arg.substring(SERVER_PORT.length());
            } else {
                recognized = false;
            }

            System.out.println((recognized ? "Recognized" : "Invalid") + " argument: " + arg);
        }

        try {
            if (homePath != null) {
                PathManager.getInstance().useOverrideHomePath(homePath);
            } else {
                PathManager.getInstance().useDefaultHomePath();
            }

        } catch (IOException e) {
            reportException(e);
            System.exit(0);
        }
    }


    private static Collection<EngineSubsystem> createSubsystemList() {
        if (isHeadless) {
            return Lists.newArrayList(new HeadlessGraphics(), new HeadlessTimer(), new HeadlessAudio(), new HeadlessInput());
        } else {
            EngineSubsystem audio = soundEnabled ? new LwjglAudio() : new HeadlessAudio();
            return Lists.<EngineSubsystem>newArrayList(new LwjglGraphics(), new LwjglTimer(), audio, new LwjglInput());
        }
    }

    private static void reportException(Throwable throwable) {
        Path logPath = LoggingContext.getLoggingPath();

        if (!GraphicsEnvironment.isHeadless() && crashReportEnabled) {
            CrashReporter.report(throwable, logPath);
        } else {
            throwable.printStackTrace();
            System.err.println("For more details, see the log files in " + logPath.toAbsolutePath().normalize());
        }
    }

    private static GameManifest getLatestGameManifest() {
        GameInfo latestGame = null;
        List<GameInfo> savedGames = GameProvider.getSavedGames();
        for (GameInfo savedGame : savedGames) {
            if (latestGame == null || savedGame.getTimestamp().after(latestGame.getTimestamp())) {
                latestGame = savedGame;
            }
        }

        if (latestGame == null) {
            return null;
        }

        return latestGame.getManifest();
    }

}


File: facades/PC/src/main/java/org/terasology/engine/splash/SplashScreenImpl.java
/*
 * Copyright 2014 MovingBlocks
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.terasology.engine.splash;

import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.Rectangle;
import java.awt.SplashScreen;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.util.Queue;

import javax.swing.SwingUtilities;
import javax.swing.Timer;

import com.google.common.collect.Queues;

/**
 * The actual implementation of {@link SplashScreenCore} that
 * uses a Swing timer to animate through a list of messages.
 * Each message is shown at least <code>n</code> frames.
 * @author Martin Steiger
 */
final class SplashScreenImpl implements SplashScreenCore {

    /**
     * In milli-seconds
     */
    private final int updateFreq = 100;

    /**
     * In frames
     */
    private final int msgUpdateFreq = 3;

    private final Timer timer;

    private final Font font = new Font("Serif", Font.BOLD, 14);

    private int frame;

    private final Queue<String> messageQueue = Queues.newConcurrentLinkedQueue();

    public SplashScreenImpl() {
        ActionListener action = new ActionListener() {

            @Override
            public void actionPerformed(ActionEvent e) {
                SplashScreen splashScreen = SplashScreen.getSplashScreen();

                if (splashScreen != null) {
                    update(splashScreen);
                } else {
                    timer.stop();
                }
            }
        };
        timer = new Timer(updateFreq, action);
        timer.setInitialDelay(0);
        timer.start();
    }

    @Override
    public void post(String message) {
        messageQueue.add(message);
    }

    @Override
    public void close() {
        SwingUtilities.invokeLater(new Runnable() {

            @Override
            public void run() {
                SplashScreen splashScreen = SplashScreen.getSplashScreen();

                if (splashScreen != null) {
                    splashScreen.close();
                }
            }
        });
    }

    private void update(SplashScreen splashScreen) {
        frame++;

        if (frame % msgUpdateFreq == 0 && messageQueue.size() > 1) {
            messageQueue.poll();
        }

        String message = messageQueue.peek();

        Rectangle rc = splashScreen.getBounds();
        Graphics2D g = splashScreen.createGraphics();
        try {
            repaint(g, rc, message);
            splashScreen.update();
        } finally {
            g.dispose();
        }
    }

    private void repaint(Graphics2D g, Rectangle rc, String text) {
        int width = 600;
        int height = 30;
        int maxTextWidth = 450;

        Color textShadowColor = new Color(224, 224, 224);

        g.setFont(font);
        g.translate(10, rc.height - height - 10);

        g.setColor(Color.WHITE);
        g.fillRect(0, 0, width, height);
        g.setColor(Color.GRAY);
        g.drawRect(0, 0, width, height);

        if (text != null) {
            FontMetrics fm = g.getFontMetrics();

            String printedText = truncateToMax(fm, text, maxTextWidth);
            int asc = g.getFontMetrics().getAscent();
            int shadowOff = 1;

            // draw shadow first
            g.setColor(textShadowColor);
            g.drawString(printedText, 10 + shadowOff, 5 + shadowOff + asc);

            // and actual text on top
            g.setColor(Color.BLACK);
            g.drawString(printedText, 10, 5 + asc);
        }

        Rectangle boxRc = new Rectangle(20 + maxTextWidth, 0, width - maxTextWidth - 30, height);
        drawBoxes(g, boxRc);
    }

    private String truncateToMax(FontMetrics fm, String text, int maxTextWidth) {
        if (text.length() < 2) {
            return text;
        }

        int texLen = text.length();
        char[] data = new char[texLen];
        text.getChars(0, texLen, data, 0);

        for (int len = 2; len <= texLen; len++) {
            if (fm.charsWidth(data, 0, len) >= maxTextWidth) {
                return text.substring(0, len - 2) + "..";
            }
        }

        return text;
    }

    private void drawBoxes(Graphics2D g, Rectangle rc) {

        int boxCount = 7;
        int boxHeight = 18;
        int boxWidth = 10;
        int space = 8;
        int dx = boxWidth + space;
        int left = rc.x + rc.width - boxCount * dx + space;

        double animSpeed = 0.05;

        for (int i = 0; i < boxCount; i++) {
            float sat = (float) Math.sin((frame - i) * Math.PI * animSpeed);
            sat = sat * sat;
            float hue = 0.6f;
            float bright = 1.0f;
            int rgb = Color.HSBtoRGB(hue, sat, bright);
            Color animColor = new Color(rgb);

            int sizeDiff = (int) Math.abs(1.0 - 2 * sat) * 2;
            int x = left + i * dx - sizeDiff / 2;
            int y = rc.y + (rc.height - boxHeight - sizeDiff) / 2;

            g.setColor(animColor);
            g.fillRect(x, y, boxWidth + sizeDiff, boxHeight + sizeDiff);

            g.setColor(Color.BLACK);
            g.drawRect(x, y, boxWidth + sizeDiff, boxHeight + sizeDiff);
        }
    }
}
