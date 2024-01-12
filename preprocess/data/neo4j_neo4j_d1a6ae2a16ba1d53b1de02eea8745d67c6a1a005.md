Refactoring Types: ['Extract Method']
in/java/org/neo4j/desktop/Neo4jDesktop.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.desktop;

import org.neo4j.desktop.config.Installation;
import org.neo4j.desktop.config.OperatingSystemFamily;
import org.neo4j.desktop.config.osx.DarwinInstallation;
import org.neo4j.desktop.config.unix.UnixInstallation;
import org.neo4j.desktop.config.windows.WindowsInstallation;
import org.neo4j.desktop.runtime.DatabaseActions;
import org.neo4j.desktop.ui.DesktopModel;
import org.neo4j.desktop.ui.MainWindow;
import org.neo4j.desktop.ui.PlatformUI;

import static org.neo4j.desktop.ui.Components.alert;

/**
 * The main class for starting the Neo4j desktop app window. The different components and wired up and started.
 */
public final class Neo4jDesktop
{
    public static void main( String[] args )
    {
        preStartInitialize();

        Neo4jDesktop app = new Neo4jDesktop();
        app.start();
    }

    public static void preStartInitialize()
    {
        PlatformUI.selectPlatformUI();
        DesktopIdentification.register();
    }

    private void start()
    {
        try
        {
            Installation installation = getInstallation();
            installation.initialize();

            DesktopModel model = new DesktopModel( installation );
            DatabaseActions databaseActions = new DatabaseActions( model );
            addShutdownHook( databaseActions );

            MainWindow window = new MainWindow( databaseActions, model );
            window.display();
        }
        catch ( Exception e )
        {
            alert( e.getMessage() );
            e.printStackTrace( System.out );
        }
    }

    private Installation getInstallation() throws Exception
    {
        switch ( OperatingSystemFamily.detect() )
        {
            case WINDOWS:
                return new WindowsInstallation();
            case MAC_OS:
                return new DarwinInstallation();
            case UNIX:
                return new UnixInstallation();
        }
        return new UnixInstallation(); // This is the most generic one, presumably.
    }

    protected void addShutdownHook( final DatabaseActions databaseActions )
    {
        Runtime.getRuntime()
                .addShutdownHook( new Thread()
                {
                    @Override
                    public void run()
                    {
                        databaseActions.stop();
                    }
                } );
    }
}


File: packaging/neo4j-desktop/src/main/java/org/neo4j/desktop/runtime/DatabaseActions.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.desktop.runtime;

import java.net.BindException;
import java.util.HashSet;
import java.util.Set;

import org.neo4j.desktop.ui.DesktopModel;
import org.neo4j.desktop.ui.MainWindow;
import org.neo4j.desktop.ui.UnableToStartServerException;
import org.neo4j.kernel.GraphDatabaseDependencies;
import org.neo4j.kernel.StoreLockException;
import org.neo4j.kernel.monitoring.Monitors;
import org.neo4j.logging.FormattedLogProvider;
import org.neo4j.logging.LogProvider;
import org.neo4j.server.AbstractNeoServer;
import org.neo4j.server.CommunityNeoServer;
import org.neo4j.server.ServerStartupException;
import org.neo4j.server.configuration.ConfigurationBuilder;

/**
 * Lifecycle actions for the Neo4j server living inside this JVM. Typically reacts to button presses
 * from {@link MainWindow}.
 */
public class DatabaseActions
{
    private final DesktopModel model;
    private AbstractNeoServer server;

    public DatabaseActions( DesktopModel model )
    {
        this.model = model;
    }

    public void start() throws UnableToStartServerException
    {
        if ( isRunning() )
        {
            throw new UnableToStartServerException( "Already started" );
        }

        ConfigurationBuilder configurator = model.getServerConfigurator();
        Monitors monitors = new Monitors();

        LogProvider userLogProvider = FormattedLogProvider.toOutputStream( System.out );
        server = new CommunityNeoServer( configurator, GraphDatabaseDependencies.newDependencies().userLogProvider( userLogProvider ).monitors( monitors ), userLogProvider );
        try
        {
            server.start();
        }
        catch ( ServerStartupException e )
        {
            server = null;
            Set<Class> causes = extractCauseTypes( e );
            if ( causes.contains( StoreLockException.class ) )
            {
                throw new UnableToStartServerException(
                        "Unable to lock store. Are you running another Neo4j process against this database?" );
            }
            if ( causes.contains( BindException.class ) )
            {
                throw new UnableToStartServerException(
                        "Unable to bind to port. Are you running another Neo4j process on this computer?" );
            }
            throw new UnableToStartServerException( e.getMessage() );
        }
    }

    private Set<Class> extractCauseTypes( Throwable e )
    {
        Set<Class> types = new HashSet<>();
        types.add( e.getClass() );
        if ( e.getCause() != null )
        {
            types.addAll( extractCauseTypes( e.getCause() ) );
        }
        return types;
    }

    public void stop()
    {
        if ( isRunning() )
        {
            server.stop();
            server = null;
        }
    }

    public void shutdown()
    {
        if ( isRunning() )
        {
            stop();
        }
    }

    public boolean isRunning()
    {
        return server != null;
    }
}


File: packaging/neo4j-desktop/src/main/java/org/neo4j/desktop/ui/BrowseForDatabaseActionListener.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.desktop.ui;

import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.File;
import javax.swing.JFileChooser;
import javax.swing.JFrame;
import javax.swing.JTextField;

import static javax.swing.JFileChooser.APPROVE_OPTION;
import static javax.swing.JFileChooser.CUSTOM_DIALOG;
import static javax.swing.JFileChooser.DIRECTORIES_ONLY;
import static javax.swing.JOptionPane.CANCEL_OPTION;
import static javax.swing.JOptionPane.ERROR_MESSAGE;
import static javax.swing.JOptionPane.OK_CANCEL_OPTION;
import static org.neo4j.desktop.ui.ScrollableOptionPane.showWrappedConfirmDialog;

class BrowseForDatabaseActionListener implements ActionListener
{
    private final JFrame frame;
    private final JTextField directoryDisplay;
    private final DesktopModel model;

    public BrowseForDatabaseActionListener( JFrame frame, JTextField directoryDisplay, DesktopModel model )
    {
        this.frame = frame;
        this.directoryDisplay = directoryDisplay;
        this.model = model;
    }

    @Override
    public void actionPerformed( ActionEvent e )
    {
        JFileChooser jFileChooser = new JFileChooser();
        jFileChooser.setFileSelectionMode( DIRECTORIES_ONLY );
        jFileChooser.setCurrentDirectory( new File( directoryDisplay.getText() ) );
        jFileChooser.setDialogTitle( "Select database" );
        jFileChooser.setDialogType( CUSTOM_DIALOG );

        while ( true )
        {
            int choice = jFileChooser.showOpenDialog( frame );

            if ( choice != APPROVE_OPTION )
            {
                return;
            }

            File selectedFile = jFileChooser.getSelectedFile();
            try
            {
                model.setDatabaseDirectory( selectedFile );
                directoryDisplay.setText( model.getDatabaseDirectory().getAbsolutePath() );
                return;
            }
            catch ( UnsuitableDirectoryException error )
            {
                int result = showWrappedConfirmDialog(
                        frame, error.getMessage() + "\nPlease choose a different folder.",
                        "Invalid folder selected", OK_CANCEL_OPTION, ERROR_MESSAGE );
                if ( result == CANCEL_OPTION )
                {
                    return;
                }
            }
        }
    }
}


File: packaging/neo4j-desktop/src/main/java/org/neo4j/desktop/ui/MainWindow.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.desktop.ui;

import java.awt.CardLayout;
import java.awt.Component;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.ImageIcon;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JTextField;

import org.neo4j.desktop.runtime.DatabaseActions;

import static javax.swing.SwingUtilities.invokeLater;

import static org.neo4j.desktop.ui.Components.createPanel;
import static org.neo4j.desktop.ui.Components.createUnmodifiableTextField;
import static org.neo4j.desktop.ui.Components.createVerticalSpacing;
import static org.neo4j.desktop.ui.Components.ellipsis;
import static org.neo4j.desktop.ui.Components.withBoxLayout;
import static org.neo4j.desktop.ui.Components.withFlowLayout;
import static org.neo4j.desktop.ui.Components.withLayout;
import static org.neo4j.desktop.ui.Components.withSpacingBorder;
import static org.neo4j.desktop.ui.Components.withTitledBorder;
import static org.neo4j.desktop.ui.DatabaseStatus.STARTED;
import static org.neo4j.desktop.ui.DatabaseStatus.STOPPED;
import static org.neo4j.desktop.ui.Graphics.loadImage;

/**
 * The main window of the Neo4j Desktop. Able to start/stop a database as well as providing access to some
 * advanced configuration options, such as heap size and database properties.
 */
public class MainWindow
{
    private final DesktopModel model;

    private final JFrame frame;
    private final DatabaseActions databaseActions;
    private final JButton browseButton;
    private final JButton startButton;
    private final JButton stopButton;
    private final CardLayout statusPanelLayout;
    private final JPanel statusPanel;
    private final JTextField directoryDisplay;
    private final SystemOutDebugWindow debugWindow;
    private final SysTray sysTray;

    private DatabaseStatus databaseStatus;

    public MainWindow( final DatabaseActions databaseActions, DesktopModel model )
    {
        this.model = model;
        this.debugWindow = new SystemOutDebugWindow();
        this.databaseActions = databaseActions;

        this.frame = new JFrame( "Neo4j Community" );
        this.frame.setIconImages( Graphics.loadIcons() );
        this.sysTray = SysTray.install( new SysTrayActions(), frame );

        this.directoryDisplay = createUnmodifiableTextField( model.getDatabaseDirectory().getAbsolutePath(), 35 );
        this.browseButton = createBrowseButton();
        this.statusPanelLayout = new CardLayout();
        this.statusPanel = createStatusPanel( statusPanelLayout );
        this.startButton = createStartButton();
        this.stopButton = createStopButton();

        JButton optionsButton = createOptionsButton();
        JPanel root =
                createRootPanel( directoryDisplay, browseButton, statusPanel, startButton, stopButton, optionsButton );

        frame.add( root );
        frame.pack();
        frame.setResizable( false );

        updateStatus( STOPPED );
    }

    private JPanel createRootPanel( JTextField directoryDisplay, JButton browseButton, Component statusPanel,
                                    JButton startButton, JButton stopButton, JButton settingsButton )
    {
        return withSpacingBorder( withBoxLayout( BoxLayout.Y_AXIS,
            createPanel( createLogoPanel(), createSelectionPanel( directoryDisplay, browseButton ), statusPanel,
                         createVerticalSpacing(), createActionPanel( startButton, stopButton, settingsButton ) ) ) );
    }

    public void display()
    {
        frame.setLocationRelativeTo( null );
        frame.setVisible( true );
    }

    private JPanel createLogoPanel()
    {
        return withFlowLayout( FlowLayout.LEFT, createPanel(
                new JLabel( new ImageIcon( loadImage( Graphics.LOGO ) ) ),
                new JLabel( model.getNeo4jVersion() ) ) );
    }

    private JPanel createActionPanel( JButton startButton, JButton stopButton, JButton settingsButton )
    {
        return withBoxLayout( BoxLayout.LINE_AXIS,
                createPanel( settingsButton, Box.createHorizontalGlue(), stopButton, startButton ) );
    }

    private JButton createOptionsButton()
    {
        return Components.createTextButton( ellipsis( "Options" ), new ActionListener()
        {
            @Override
            public void actionPerformed( ActionEvent e )
            {
                JDialog settingsDialog = new SettingsDialog( frame, model );
                settingsDialog.setLocationRelativeTo( null );
                settingsDialog.setVisible( true );
            }
        } );
    }

    private JPanel createSelectionPanel( JTextField directoryDisplay, JButton selectButton )
    {
        return withTitledBorder( "Database location", withBoxLayout( BoxLayout.LINE_AXIS,
                createPanel( directoryDisplay, selectButton ) ) );
    }

    protected void shutdown()
    {
        databaseActions.shutdown();
        debugWindow.dispose();
        frame.dispose();
        System.exit( 0 );
    }

    private JPanel createStatusPanel( CardLayout statusPanelLayout )
    {
        JPanel panel = withLayout( statusPanelLayout, withTitledBorder( "Status", createPanel() ) );
        for ( DatabaseStatus status : DatabaseStatus.values() )
        {
            panel.add( status.name(), status.display( model ) );
        }

        panel.addMouseListener( new MouseAdapter()
        {
            @Override
            public void mouseClicked( MouseEvent e )
            {
                if ( MouseEvent.BUTTON1 == e.getButton() && e.isAltDown() )
                {
                    debugWindow.show();
                }
            }
        } );
        return panel;
    }

    private JButton createBrowseButton()
    {
        ActionListener actionListener = new BrowseForDatabaseActionListener( frame, directoryDisplay, model );
        return Components.createTextButton( ellipsis( "Browse" ), actionListener );
    }

    private JButton createStartButton()
    {
        return Components.createTextButton( "Start", new StartDatabaseActionListener( this, model, databaseActions ) );
    }

    private JButton createStopButton()
    {
        return Components.createTextButton( "Stop", new ActionListener()
        {
            @Override
            public void actionPerformed( ActionEvent e )
            {
                updateStatus( DatabaseStatus.STOPPING );

                invokeLater( new Runnable()
                {
                    @Override
                    public void run()
                    {
                        databaseActions.stop();
                        updateStatus( STOPPED );
                    }
                } );
            }
        } );
    }

    public void updateStatus( DatabaseStatus status )
    {
        browseButton.setEnabled( STOPPED == status );
        startButton.setEnabled( STOPPED == status );
        stopButton.setEnabled( STARTED == status );
        statusPanelLayout.show( statusPanel, status.name() );
        databaseStatus = status;
        sysTray.changeStatus( status );
    }

    private class SysTrayActions implements SysTray.Actions
    {
        @Override
        public void closeForReal()
        {
            shutdown();
        }

        @Override
        public void clickSysTray()
        {
            frame.setVisible( true );
        }

        @Override
        public void clickCloseButton()
        {
            if ( databaseStatus == STOPPED )
            {
                shutdown();
            }
            else
            {
                frame.setVisible( false );
            }
        }
    }
}


File: packaging/neo4j-desktop/src/main/java/org/neo4j/desktop/ui/SysTray.java
/*
 * Copyright (c) 2002-2015 "Neo Technology,"
 * Network Engine for Objects in Lund AB [http://neotechnology.com]
 *
 * This file is part of Neo4j.
 *
 * Neo4j is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
package org.neo4j.desktop.ui;

import java.awt.AWTException;
import java.awt.SystemTray;
import java.awt.TrayIcon;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import javax.swing.JFrame;

import static javax.swing.WindowConstants.DO_NOTHING_ON_CLOSE;

import static org.neo4j.desktop.ui.DatabaseStatus.STOPPED;
import static org.neo4j.desktop.ui.Graphics.loadImage;

/**
 * Adds {@link SystemTray} integration to Neo4j Desktop. Call {@link #install(org.neo4j.desktop.ui.SysTray.Actions,
 * javax.swing.JFrame)} to install it
 * where a {@link Enabled} instance will be returned if the system tray functionality is supported on this system.
 */
public abstract class SysTray
{
    public static SysTray install( Actions actions, JFrame mainWindow )
    {
        try
        {
            if ( SystemTray.isSupported() )
            {
                return new SysTray.Enabled( Graphics.SYSTEM_TRAY_ICON, actions, mainWindow );
            }
        }
        catch ( AWTException e )
        {
            // What to do here?
            e.printStackTrace( System.out );
        }
        
        // Fall back to still being able to function, but without the systray support.
        return new SysTray.Disabled( actions, mainWindow );
    }
    
    public abstract void changeStatus( DatabaseStatus status );
    
    private static class Enabled extends SysTray
    {
        private final TrayIcon trayIcon;
        private final String iconResourceBaseName;
        
        Enabled( String iconResourceBaseName, Actions actions, JFrame mainWindow ) throws AWTException
        {
            this.iconResourceBaseName = iconResourceBaseName;
            this.trayIcon = init( actions, mainWindow );
        }

        @Override
        public void changeStatus( DatabaseStatus status )
        {
            trayIcon.setImage( loadImage( tryStatusSpecific( status ) ) );
            trayIcon.setToolTip( title( status ) );
        }

        private String tryStatusSpecific( DatabaseStatus status )
        {
            String iconResource = status.name() + "-" + iconResourceBaseName;
            return SysTray.class.getResource( iconResource ) != null ? iconResource : iconResourceBaseName;
        }

        private TrayIcon init( final Actions actions, JFrame mainWindow )
                throws AWTException
        {
            TrayIcon trayIcon = new TrayIcon( loadImage( tryStatusSpecific( STOPPED ) ), title( STOPPED ) );
            trayIcon.addActionListener( new ActionListener()
            {
                @Override
                public void actionPerformed( ActionEvent e )
                {
                    actions.clickSysTray();
                }
            } );
            trayIcon.addMouseListener( new MouseAdapter()
            {
                @Override
                public void mouseClicked( MouseEvent e )
                {
                    actions.clickSysTray();
                }
            } );
            mainWindow.setDefaultCloseOperation( DO_NOTHING_ON_CLOSE );
            mainWindow.addWindowListener( new WindowAdapter()
            {
                @Override
                public void windowClosing( WindowEvent e )
                {
                    actions.clickCloseButton();
                }
            } );
            SystemTray.getSystemTray().add( trayIcon );
            return trayIcon;
        }

        private String title( DatabaseStatus status )
        {
            return "Neo4j Community (" + status.name() + ")";
        }
    }
    
    private static class Disabled extends SysTray
    {
        Disabled( final Actions actions, JFrame mainWindow )
        {
            mainWindow.setDefaultCloseOperation( DO_NOTHING_ON_CLOSE );
            mainWindow.addWindowListener( new WindowAdapter()
            {
                @Override
                public void windowClosing( WindowEvent e )
                {
                    actions.closeForReal();
                }
            } );
        }
        
        @Override
        public void changeStatus( DatabaseStatus status )
        {
            // Don't do anything.
        }
    }
    
    public interface Actions
    {
        void clickCloseButton();
        
        void clickSysTray();
        
        void closeForReal();
    }
}
