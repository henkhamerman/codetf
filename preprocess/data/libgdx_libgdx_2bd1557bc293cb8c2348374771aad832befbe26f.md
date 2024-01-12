Refactoring Types: ['Inline Method']
es/scene2d/ui/CheckBox.java
/*******************************************************************************
 * Copyright 2011 See AUTHORS file.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ******************************************************************************/

package com.badlogic.gdx.scenes.scene2d.ui;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.scenes.scene2d.utils.Drawable;
import com.badlogic.gdx.utils.Align;

/** A checkbox is a button that contains an image indicating the checked or unchecked state and a label.
 * @author Nathan Sweet */
public class CheckBox extends TextButton {
	private Image image;
	private Cell imageCell;
	private CheckBoxStyle style;

	public CheckBox (String text, Skin skin) {
		this(text, skin.get(CheckBoxStyle.class));
	}

	public CheckBox (String text, Skin skin, String styleName) {
		this(text, skin.get(styleName, CheckBoxStyle.class));
	}

	public CheckBox (String text, CheckBoxStyle style) {
		super(text, style);
		clearChildren();
		setCheckBoxRight(false);
		getLabel().setAlignment(Align.left);
		setSize(getPrefWidth(), getPrefHeight());
	}

	public void setCheckBoxRight (boolean right) {
		Label label = getLabel();
		if (right) {
			add(label);
			imageCell = add(image = new Image(style.checkboxOff));
		} else {
			imageCell = add(image = new Image(style.checkboxOff));
			add(label);
		}
	}

	public void setStyle (ButtonStyle style) {
		if (!(style instanceof CheckBoxStyle)) throw new IllegalArgumentException("style must be a CheckBoxStyle.");
		super.setStyle(style);
		this.style = (CheckBoxStyle)style;
	}

	/** Returns the checkbox's style. Modifying the returned style may not have an effect until {@link #setStyle(ButtonStyle)} is
	 * called. */
	public CheckBoxStyle getStyle () {
		return style;
	}

	public void draw (Batch batch, float parentAlpha) {
		Drawable checkbox = null;
		if (isDisabled()) {
			if (isChecked && style.checkboxOnDisabled != null)
				checkbox = style.checkboxOnDisabled;
			else
				checkbox = style.checkboxOffDisabled;
		}
		if (checkbox == null) {
			if (isChecked && style.checkboxOn != null)
				checkbox = style.checkboxOn;
			else if (isOver() && style.checkboxOver != null && !isDisabled())
				checkbox = style.checkboxOver;
			else
				checkbox = style.checkboxOff;
		}
		image.setDrawable(checkbox);
		super.draw(batch, parentAlpha);
	}

	public Image getImage () {
		return image;
	}

	public Cell getImageCell () {
		return imageCell;
	}

	/** The style for a select box, see {@link CheckBox}.
	 * @author Nathan Sweet */
	static public class CheckBoxStyle extends TextButtonStyle {
		public Drawable checkboxOn, checkboxOff;
		/** Optional. */
		public Drawable checkboxOver, checkboxOnDisabled, checkboxOffDisabled;

		public CheckBoxStyle () {
		}

		public CheckBoxStyle (Drawable checkboxOff, Drawable checkboxOn, BitmapFont font, Color fontColor) {
			this.checkboxOff = checkboxOff;
			this.checkboxOn = checkboxOn;
			this.font = font;
			this.fontColor = fontColor;
		}

		public CheckBoxStyle (CheckBoxStyle style) {
			this.checkboxOff = style.checkboxOff;
			this.checkboxOn = style.checkboxOn;
			this.checkboxOver = style.checkboxOver;
			this.checkboxOffDisabled = style.checkboxOffDisabled;
			this.checkboxOnDisabled = style.checkboxOnDisabled;
			this.font = style.font;
			this.fontColor = new Color(style.fontColor);
		}
	}
}


File: tests/gdx-tests/src/com/badlogic/gdx/tests/Scene2dTest.java
/*******************************************************************************
 * Copyright 2011 See AUTHORS file.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ******************************************************************************/

package com.badlogic.gdx.tests;

import static com.badlogic.gdx.scenes.scene2d.actions.Actions.*;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.Batch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.scenes.scene2d.Actor;
import com.badlogic.gdx.scenes.scene2d.InputEvent;
import com.badlogic.gdx.scenes.scene2d.InputListener;
import com.badlogic.gdx.scenes.scene2d.Stage;
import com.badlogic.gdx.scenes.scene2d.actions.FloatAction;
import com.badlogic.gdx.scenes.scene2d.ui.CheckBox;
import com.badlogic.gdx.scenes.scene2d.ui.HorizontalGroup;
import com.badlogic.gdx.scenes.scene2d.ui.ImageTextButton;
import com.badlogic.gdx.scenes.scene2d.ui.ImageTextButton.ImageTextButtonStyle;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.Skin;
import com.badlogic.gdx.scenes.scene2d.ui.Table;
import com.badlogic.gdx.scenes.scene2d.ui.TextButton;
import com.badlogic.gdx.scenes.scene2d.ui.TextButton.TextButtonStyle;
import com.badlogic.gdx.scenes.scene2d.ui.VerticalGroup;
import com.badlogic.gdx.scenes.scene2d.ui.Window;
import com.badlogic.gdx.scenes.scene2d.utils.ActorGestureListener;
import com.badlogic.gdx.scenes.scene2d.utils.TiledDrawable;
import com.badlogic.gdx.tests.utils.GdxTest;

public class Scene2dTest extends GdxTest {
	Stage stage;
	private FloatAction meow = new FloatAction(10, 5);
	private TiledDrawable patch;

	public void create () {
		stage = new Stage();
		Gdx.input.setInputProcessor(stage);

		final TextureRegion region = new TextureRegion(new Texture("data/badlogic.jpg"));
		final Actor actor = new Actor() {
			public void draw (Batch batch, float parentAlpha) {
				Color color = getColor();
				batch.setColor(color.r, color.g, color.b, parentAlpha);
				batch.draw(region, getX(), getY(), getOriginX(), getOriginY(), getWidth(), getHeight(), getScaleX(), getScaleY(),
					getRotation());
			}
		};
		actor.setBounds(15, 15, 100, 100);
		actor.setOrigin(50, 50);
		stage.addActor(actor);
		actor.addListener(new InputListener() {
			public boolean touchDown (InputEvent event, float x, float y, int pointer, int button) {
				System.out.println("down");
				return true;
			}

			public void touchUp (InputEvent event, float x, float y, int pointer, int button) {
				System.out.println("up " + event.getTarget());
			}
		});

		Skin skin = new Skin(Gdx.files.internal("data/uiskin.json"));

		VerticalGroup g = new VerticalGroup().space(5).reverse().pad(5).fill();
		for (int i = 0; i < 10; i++)
			g.addActor(new TextButton("button " + i, skin));
		g.addActor(new TextButton("longer button", skin));
		Table table = new Table().debug();
		table.add(g);
		table.pack();
		table.setPosition(5, 100);
		stage.addActor(table);

		HorizontalGroup h = new HorizontalGroup().space(5).reverse().pad(5).fill();
		for (int i = 0; i < 5; i++)
			h.addActor(new TextButton("button " + i, skin));
		h.addActor(new TextButton("some taller\nbutton", skin));
		table = new Table().debug();
		table.add(h);
		table.pack();
		table.setPosition(130, 100);
		stage.addActor(table);
		table.toFront();

		final TextButton button = new TextButton("Fancy Background", skin);

// button.addListener(new ClickListener() {
// public void clicked (InputEvent event, float x, float y) {
// System.out.println("click! " + x + " " + y);
// }
// });

		button.addListener(new ActorGestureListener() {
			public boolean longPress (Actor actor, float x, float y) {
				System.out.println("long press " + x + ", " + y);
				return true;
			}

			public void fling (InputEvent event, float velocityX, float velocityY, int button) {
				System.out.println("fling " + velocityX + ", " + velocityY);
			}

			public void zoom (InputEvent event, float initialDistance, float distance) {
				System.out.println("zoom " + initialDistance + ", " + distance);
			}

			public void pan (InputEvent event, float x, float y, float deltaX, float deltaY) {
				event.getListenerActor().moveBy(deltaX, deltaY);
				if (deltaX < 0) System.out.println("panning " + deltaX + ", " + deltaY + " " + event.getTarget());
			}
		});

// button.addListener(new ChangeListener() {
// public void changed (ChangeEvent event, Actor actor) {
// // event.cancel();
// }
// });

		button.setPosition(50, 50);
		stage.addActor(button);

// List select = new List(skin);
// select.setBounds(200, 200, 100, 100);
// select.setItems(new Object[] {1, 2, 3, 4, 5});
// stage.addActor(select);

// stage.addListener(new ChangeListener() {
// public void changed (ChangeEvent event, Actor actor) {
// System.out.println(actor);
// }
// });

		meow.setDuration(2);

		actor.addAction(forever(sequence(moveBy(50, 0, 2), moveBy(-50, 0, 2), run(new Runnable() {
			public void run () {
				actor.setZIndex(0);
			}
		}))));
		// actor.addAction(parallel(rotateBy(90, 2), rotateBy(90, 2)));
		// actor.addAction(parallel(moveTo(250, 250, 2, elasticOut), color(RED, 6), delay(0.5f), rotateTo(180, 5, swing)));
		// actor.addAction(forever(sequence(scaleTo(2, 2, 0.5f), scaleTo(1, 1, 0.5f), delay(0.5f))));

		patch = new TiledDrawable(skin.getRegion("default-round"));

		Window window = new Window("Moo", skin);
		Label lbl = new Label("ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJ", skin);
		lbl.setWrap(true);
		window.row();
		window.add(lbl).width(400);
		window.pack();
		window.pack();
		stage.addActor(window);

		ImageTextButtonStyle style = new ImageTextButtonStyle(skin.get("default", TextButtonStyle.class));
		style.imageUp = skin.getDrawable("default-round");
		ImageTextButton buttonLeft = new ImageTextButton("HI IM LEFT", style);
		ImageTextButton buttonRight = new ImageTextButton("HI IM RIGHT", style) {
			{
				clearChildren();
				add(getLabel());
				add(getImage());
			}
		};
		CheckBox checkBoxLeft = new CheckBox("HI IM LEFT", skin, "default");
		CheckBox checkBoxRight = new CheckBox("HI IM RIGHT", skin, "default");
		checkBoxRight.setCheckBoxRight(true);

		buttonLeft.setPosition(300, 400);
		buttonRight.setPosition(300, 370);
		checkBoxLeft.setPosition(150, 400);
		checkBoxRight.setPosition(150, 370);

		stage.addActor(buttonLeft);
		stage.addActor(buttonRight);
		stage.addActor(checkBoxLeft);
		stage.addActor(checkBoxRight);

		buttonLeft.debug();
		buttonRight.debug();
		checkBoxLeft.debug();
		checkBoxRight.debug();
	}

	public void render () {
		// System.out.println(meow.getValue());
		Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
		stage.act(Gdx.graphics.getDeltaTime());
		stage.draw();

		stage.getBatch().begin();
		patch.draw(stage.getBatch(), 300, 100, 126, 126);
		stage.getBatch().end();
	}

	public void resize (int width, int height) {
		stage.getViewport().update(width, height, true);
	}

	public void dispose () {
		stage.dispose();
	}
}
