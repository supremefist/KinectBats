using System;
using System.Collections.Generic;
using System.Linq;
using System.Diagnostics;

using System.Speech.AudioFormat;
using System.Speech.Recognition;
using System.IO;

using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Audio;
using Microsoft.Xna.Framework.Content;
using Microsoft.Xna.Framework.GamerServices;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using Microsoft.Xna.Framework.Media;

using FarseerPhysics;
using FarseerPhysics.Dynamics;
using FarseerPhysics.Factories;
using FarseerPhysics.Common;
using FarseerPhysics.Common.PolygonManipulation;
using FarseerPhysics.Dynamics.Joints;
using FarseerPhysics.Collision.Shapes;

using Microsoft.Kinect;

namespace KinectBats
{
    /// <summary>
    /// This is the main type for your game
    /// </summary>
    public class KinectBats : Game
    {
        World world;

        private SpeechRecognitionEngine speechRecognizer;
        
        float worldSimWidth = 8f;
        float worldSimHeight = 6f;

        DateTime lastAcknowledgeTime;

        GraphicsDeviceManager graphics;
        SpriteBatch spriteBatch;
        KinectSensor kinect;
        Texture2D colorVideo, depthVideo;
        Boolean debugging = true;
        Boolean done = false;
        Boolean commandExecuted = false;
        const int skeletonCount = 6;
        Skeleton[] allSkeletons = new Skeleton[skeletonCount];
        CoordinateMapper cm;

        int leftScore = 0;
        int rightScore = 0;

        int targetScore = 6;

        SpriteFont font;

        Grammar selectGrammar;
        Grammar startGrammar;

        Texture2D marker;
        Texture2D marker2;
        Texture2D pixel;
        Texture2D armTexture;
        Texture2D ballTexture;

        ColorImagePoint leftHandPoint;
        ColorImagePoint leftElbowPoint;
        bool leftTracked = false;

        ColorImagePoint rightHandPoint;
        ColorImagePoint rightElbowPoint;
        bool rightTracked = false;

        Line l;

        const DepthImageFormat depthFormat = DepthImageFormat.Resolution320x240Fps30;
        const ColorImageFormat colorFormat = ColorImageFormat.RgbResolution640x480Fps30;

        List<Body> bodies = new List<Body>();
        List<Texture2D> textures = new List<Texture2D>();
        List<Vector2> origins = new List<Vector2>();

        Boolean listening = false;

        Body leftArm;
        FixedMouseJoint leftHandJoint;
        FixedMouseJoint leftElbowJoint;

        Body rightArm;
        FixedMouseJoint rightHandJoint;
        FixedMouseJoint rightElbowJoint;

        Body ballBody = null;
        CircleShape ballShape;
        Vector2 ballOrigin;

        SoundEffect acknowledgeSound;
        SoundEffect affirmativeSound;
        SoundEffect bogusSound;
        SoundEffect goalSound;
        SoundEffect awaitingSound;

        public KinectBats()
        {
            // 1 meter = 64 pixels
            ConvertUnits.SetDisplayUnitToSimUnitRatio(160f);

            graphics = new GraphicsDeviceManager(this);
            graphics.IsFullScreen = false;
            graphics.PreferredBackBufferHeight = (int)ConvertUnits.ToDisplayUnits(worldSimHeight);
            graphics.PreferredBackBufferWidth = (int)ConvertUnits.ToDisplayUnits(worldSimWidth);
            //Changes the settings that you just applied
            graphics.ApplyChanges();

            Content.RootDirectory = "Content";

            lastAcknowledgeTime = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        }

        private static RecognizerInfo GetKinectRecognizer()
        {
            Func<RecognizerInfo, bool> matchingFunc = r =>
            {
                return "en-GB".Equals(r.Culture.Name, StringComparison.InvariantCultureIgnoreCase);
            };

            RecognizerInfo result = SpeechRecognitionEngine.InstalledRecognizers().Where(matchingFunc).FirstOrDefault();
            if (result == null)
            {
                Console.WriteLine("No recogniser found");
            }
            return result;
        }

        public void resetGame()
        {
            leftScore = 0;
            rightScore = 0;

            resetBall();
        }

        public void resetBall()
        {
            if (ballBody != null)
            {
                world.RemoveBody(ballBody);
                ballBody = null;
            }

            //Create an array to hold the data from the texture
            uint[] data = new uint[ballTexture.Width * ballTexture.Height];

            //Transfer the texture data to the array
            ballTexture.GetData(data);

            //Find the vertices that makes up the outline of the shape in the texture
            Vertices textureVertices = PolygonTools.CreatePolygon(data, ballTexture.Width, false);

            Vector2 centroid = -textureVertices.GetCentroid();
            textureVertices.Translate(ref centroid);
            
            ballOrigin = -centroid;

            //We simplify the vertices found in the texture.
            textureVertices = SimplifyTools.ReduceByDistance(textureVertices, 4f);
            float scale = 1.0f;
            Vector2 vertScale = new Vector2(ConvertUnits.ToSimUnits(1)) * scale;
            textureVertices.Scale(vertScale);

            //Create a single body with multiple fixtures
            ballBody = BodyFactory.CreateBody(world);
            ballBody.BodyType = BodyType.Dynamic;
            ballBody.Position = new Vector2(worldSimWidth / 2, worldSimWidth / 5);
            Fixture temp = ballBody.CreateFixture(ballShape);

            ballBody.Restitution = 0.95f;
            ballBody.Friction = 0.95f;
        }

        private void startAudio(KinectSensor sensor)
        {
            Console.WriteLine("Starting audo...");

            //set sensor audio source to variable
            var audioSource = sensor.AudioSource;
            //Set the beam angle mode - the direction the audio beam is pointing
            //we want it to be set to adaptive
            audioSource.BeamAngleMode = BeamAngleMode.Adaptive;
            //start the audiosource 
            var kinectStream = audioSource.Start();

            Console.WriteLine("Started...");

            speechRecognizer = CreateSpeechRecognizer();

            Console.WriteLine("Created recogniser.");

            //configure incoming audio stream
            speechRecognizer.SetInputToAudioStream(
                kinectStream, new SpeechAudioFormatInfo(EncodingFormat.Pcm, 16000, 16, 1, 32000, 2, null));
            //make sure the recognizer does not stop after completing     
            speechRecognizer.RecognizeAsync(RecognizeMode.Multiple);
            //reduce background and ambient noise for better accuracy
            sensor.AudioSource.EchoCancellationMode = EchoCancellationMode.None;
            sensor.AudioSource.AutomaticGainControlEnabled = false;

            

            Console.WriteLine("GO");
        }

        private void RejectSpeech(RecognitionResult result)
        {
            Console.WriteLine("Pardon Moi?");
        }

        private void SreSpeechRecognitionRejected(object sender, SpeechRecognitionRejectedEventArgs e)
        {
            RejectSpeech(e.Result);
        }

        //hypothesized result
        private void SreSpeechHypothesized(object sender, SpeechHypothesizedEventArgs e)
        {
            Console.WriteLine("Hypothesized: " + e.Result.Text + " " + e.Result.Confidence);
        }

        //Speech is recognised
        private void SreSpeechRecognized(object sender, SpeechRecognizedEventArgs e)
        {
            //Very important! - change this value to adjust accuracy - the higher the value
            //the more accurate it will have to be, lower it if it is not recognizing you

            if (e.Result.Confidence < .1)
            {
                lastAcknowledgeTime = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

                //MediaPlayer.Play(bogusSound);
                
                RejectSpeech(e.Result);
            }

            
            //and finally, here we set what we want to happen when 
            //the SRE recognizes a word
            String word = e.Result.Text.ToUpperInvariant();
            
            if (word == "COMPUTER") {
                //acknowledgeSound.Play();
                lastAcknowledgeTime = DateTime.Now;

                speechRecognizer.RequestRecognizerUpdate();
                speechRecognizer.UnloadAllGrammars();
                speechRecognizer.LoadGrammarAsync(selectGrammar);

                listening = true;
            }
            else if (word == "EXIT")
            {
                //affirmativeSound.Play();
                this.Exit();
                commandExecuted = true;
            }
            else if (word == "RESET BALL")
            {
                affirmativeSound.Play();
                resetBall();
                commandExecuted = true;
            }
            else if (word == "RESTART")
            {
                affirmativeSound.Play();
                resetGame();
                commandExecuted = true;
            }
            else if (word == "SHUT UP")
            {
                bogusSound.Play();
                commandExecuted = true;
            }
            
        }


        //here is the fun part: create the speech recognizer
        private SpeechRecognitionEngine CreateSpeechRecognizer()
        {
            //set recognizer info
            RecognizerInfo ri = GetKinectRecognizer();

            //create instance of SRE
            SpeechRecognitionEngine sre;
            sre = new SpeechRecognitionEngine(ri.Id);

            var startChoices = new Choices();
            startChoices.Add("computer");
            
            //Now we need to add the words we want our program to recognise
            var grammar = new Choices();
            grammar.Add("exit");
            grammar.Add("reset ball");
            grammar.Add("restart");
            grammar.Add("shut up");

            //set culture - language, country/r balegionit
            var gb = new GrammarBuilder { Culture = ri.Culture };
            gb.Append(grammar);

            var startgb = new GrammarBuilder { Culture = ri.Culture };
            startgb.Append(startChoices);

            //set up the grammar builder
            selectGrammar = new Grammar(gb);
            startGrammar = new Grammar(startgb);
            sre.LoadGrammar(startGrammar);

            //Set events for recognizing, hypothesising and rejecting speech
            sre.SpeechRecognized += SreSpeechRecognized;
            sre.SpeechHypothesized += SreSpeechHypothesized;
            sre.SpeechRecognitionRejected += SreSpeechRecognitionRejected;

            return sre;
        }

        /// <summary>
        /// Allows the game to perform any initialization it needs to before starting to run.
        /// This is where it can query for any required services and load any non-graphic
        /// related content.  Calling base.Initialize will enumerate through any components
        /// and initialize them as well.
        /// </summary>
        protected override void Initialize()
        {

            try
            {
                if (KinectSensor.KinectSensors.Count > 0)
                {
                    //Initialise Kinect
                    kinect = KinectSensor.KinectSensors[0];

                    if (kinect.Status == KinectStatus.Connected)
                    {
                        kinect.ColorStream.Enable(colorFormat);
                        kinect.DepthStream.Enable(depthFormat);

                        TransformSmoothParameters smoothingParam = new TransformSmoothParameters();
                        {
                            smoothingParam.Smoothing = 0.5f;
                            smoothingParam.Correction = 0.5f;
                            smoothingParam.Prediction = 0.5f;
                            smoothingParam.JitterRadius = 0.05f;
                            smoothingParam.MaxDeviationRadius = 0.04f;
                        };
                        
                        //kinect.SkeletonStream.Enable(smoothingParam);
                        kinect.SkeletonStream.Enable();

                        kinect.AllFramesReady += new EventHandler<AllFramesReadyEventArgs>(kinect_AllFramesReady);

                        kinect.Start();

                        cm = new CoordinateMapper(kinect);
                        Debug.WriteLineIf(debugging, kinect.Status);

                        //startAudio(kinect);
                    }

                    
                }
            }
            catch (Exception e)
            {
                Debug.WriteLine(e.ToString());
            }

            base.Initialize();

            //l = new Line(new Vector2(0, 0), new Vector2(100, 100), 20, Color.Black, pixel);
        }

        Skeleton[] GetPlayerSkeletons(AllFramesReadyEventArgs e)
        {
            using (SkeletonFrame frame = e.OpenSkeletonFrame())
            {
                Skeleton[] trackedSkeletons = new Skeleton[2];

                if (frame == null)
                {
                    return trackedSkeletons;
                }

                frame.CopySkeletonDataTo(allSkeletons);

                //(Skeleton[])(from s in allSkeletons where s.TrackingState == SkeletonTrackingState.Tracked);
                var firstFound = false;

                for (int i = 0; i < skeletonCount; i++)
                {
                    if (allSkeletons[i].TrackingState == SkeletonTrackingState.Tracked)
                    {
                        if (!firstFound)
                        {
                            trackedSkeletons[0] = allSkeletons[i];
                            firstFound = true;
                        }
                        else
                        {
                            trackedSkeletons[1] = allSkeletons[i];
                        }
                    }
                }

                return trackedSkeletons;
            }
        }

        private Body addRectangleObject(float width, float height, float x, float y, bool dynamic)
        {

            int pixelWidth = (int)Math.Round(ConvertUnits.ToDisplayUnits(width));
            int pixelHeight = (int)Math.Round(ConvertUnits.ToDisplayUnits(height));
            Texture2D rectangleTexture = new Texture2D(graphics.GraphicsDevice, pixelWidth, pixelHeight);
            // Create a color array for the pixels
            Color[] colors = new Color[pixelWidth * pixelHeight];
            for (int i = 0; i < colors.Length; i++)
            {
                colors[i] = new Color(Color.White.ToVector3());
            }

            // Set the color data for the texture
            rectangleTexture.SetData(colors);

            return addObjectFromTexture(rectangleTexture, x, y, dynamic);
        }

        private Body addObjectFromTexture(Texture2D texture, float x, float y, bool dynamic)
        {
            //Create an array to hold the data from the texture
            uint[] data = new uint[texture.Width * texture.Height];

            //Transfer the texture data to the array
            texture.GetData(data);

            //Find the vertices that makes up the outline of the shape in the texture
            Vertices textureVertices = PolygonTools.CreatePolygon(data, texture.Width, false);

            //The tool return vertices as they were found in the texture.
            //We need to find the real center (centroid) of the vertices for 2 reasons:

            //1. To translate the vertices so the polygon is centered around the centroid.
            Vector2 centroid = -textureVertices.GetCentroid();
            textureVertices.Translate(ref centroid);

            //2. To draw the texture the correct place.
            var objectOrigin = -centroid;

            //We simplify the vertices found in the texture.
            textureVertices = SimplifyTools.ReduceByDistance(textureVertices, 4f);
            float scale = 1.0f;
            Vector2 vertScale = new Vector2(ConvertUnits.ToSimUnits(1)) * scale;
            textureVertices.Scale(vertScale);

            //Create a single body with multiple fixtures
            var body = BodyFactory.CreatePolygon(world, textureVertices, 1f, BodyType.Dynamic);
            body.CollisionGroup = 0;
            body.Position = new Vector2(x, y);

            if (dynamic)
            {
                body.BodyType = BodyType.Dynamic;
            }
            else
            {
                body.BodyType = BodyType.Static;
            }

            bodies.Add(body);
            textures.Add(texture);
            origins.Add(objectOrigin);

            return body;
        }
        
        private byte[] ConvertDepthFrame(short[] depthFrame, DepthImageStream depthStream)
        {
            int RedIndex = 0, GreenIndex = 1, BlueIndex = 2, AlphaIndex = 3;

            byte[] depthFrame32 = new byte[depthStream.FrameWidth * depthStream.FrameHeight * 4];

            for (int i16 = 0, i32 = 0; i16 < depthFrame.Length && i32 < depthFrame32.Length; i16++, i32 += 4)
            {
                int player = depthFrame[i16] & DepthImageFrame.PlayerIndexBitmask;
                int realDepth = depthFrame[i16] >> DepthImageFrame.PlayerIndexBitmaskWidth;

                // transform 13-bit depth information into an 8-bit intensity appropriate
                // for display (we disregard information in most significant bit)
                byte intensity = (byte)(~(realDepth >> 4));

                depthFrame32[i32 + RedIndex] = (byte)(intensity);
                depthFrame32[i32 + GreenIndex] = (byte)(intensity);
                depthFrame32[i32 + BlueIndex] = (byte)(intensity);
                depthFrame32[i32 + AlphaIndex] = 255;
            }
            return depthFrame32;
        }

        void kinect_AllFramesReady(object sender, AllFramesReadyEventArgs imageFrames)
        {
            if (done)
            {
                return;
            }

            kinect_ColorFrameReady(sender, imageFrames);
            Skeleton[] skeletons = GetPlayerSkeletons(imageFrames);

            if (skeletons[0] != null)
            {
                UpdateSkeleton(skeletons[0], imageFrames, 0);
            }
            else
            {
                leftTracked = false;
            }

            if (skeletons[1] != null)
            {
                UpdateSkeleton(skeletons[1], imageFrames, 1);
            }
            else
            {
                rightTracked = false;
            }

        }

        void kinect_ColorFrameReady(object sender, AllFramesReadyEventArgs imageFrames)
        {
            //Get raw image
            ColorImageFrame colorVideoFrame = imageFrames.OpenColorImageFrame();

            if (colorVideoFrame != null)
            {
                //Create array for pixel data and copy it from the image frame
                Byte[] pixelData = new Byte[colorVideoFrame.PixelDataLength];
                colorVideoFrame.CopyPixelDataTo(pixelData);

                //Convert RGBA to BGRA
                Byte[] bgraPixelData = new Byte[colorVideoFrame.PixelDataLength];
                for (int i = 0; i < pixelData.Length; i += 4)
                {
                    bgraPixelData[i] = pixelData[i + 2];
                    bgraPixelData[i + 1] = pixelData[i + 1];
                    bgraPixelData[i + 2] = pixelData[i];
                    bgraPixelData[i + 3] = (Byte)255; //The video comes with 0 alpha so it is transparent
                }

                // Create a texture and assign the realigned pixels
                colorVideo = new Texture2D(graphics.GraphicsDevice, colorVideoFrame.Width, colorVideoFrame.Height);
                colorVideo.SetData(bgraPixelData);

                colorVideoFrame.Dispose();
            }

            
        }

        void UpdateSkeleton(Skeleton s, AllFramesReadyEventArgs e, int index)
        {
            using (DepthImageFrame depth = e.OpenDepthImageFrame())
            {
                if (depth == null || kinect == null)
                {
                    return;
                }

                bool tracked = true;
                if ((s.Joints[Microsoft.Kinect.JointType.HandRight].TrackingState != JointTrackingState.Tracked) || (s.Joints[Microsoft.Kinect.JointType.HandRight].TrackingState != JointTrackingState.Tracked))
                {
                    tracked = false;
                }

                DepthImagePoint leftHandDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[Microsoft.Kinect.JointType.HandRight].Position, depthFormat);
                DepthImagePoint leftElbowDepthPoint = cm.MapSkeletonPointToDepthPoint(s.Joints[Microsoft.Kinect.JointType.ElbowRight].Position, depthFormat);

                if (index == 0)
                {
                    leftHandPoint = cm.MapDepthPointToColorPoint(depthFormat, leftHandDepthPoint, colorFormat);
                    leftElbowPoint = cm.MapDepthPointToColorPoint(depthFormat, leftElbowDepthPoint, colorFormat);
                    leftTracked = tracked;
                }
                else {
                    rightHandPoint = cm.MapDepthPointToColorPoint(depthFormat, leftHandDepthPoint, colorFormat);
                    rightElbowPoint = cm.MapDepthPointToColorPoint(depthFormat, leftElbowDepthPoint, colorFormat);
                    rightTracked = tracked;
                }
            }
        }

        private void JointBroke(object sender, EventArgs e)
        {
            Console.WriteLine("BROKEN");
        }

        /// <summary>
        /// LoadContent will be called once per game and is the place to load
        /// all of your content.
        /// </summary>
        protected override void LoadContent()
        {
            // Create a new SpriteBatch, which can be used to draw textures.
            spriteBatch = new SpriteBatch(GraphicsDevice);

            // TODO: use this.Content to load your game content here
            pixel = this.Content.Load<Texture2D>("pixel");
            marker = this.Content.Load<Texture2D>("marker");
            marker2 = this.Content.Load<Texture2D>("marker2");
            armTexture = this.Content.Load<Texture2D>("arm");
            ballTexture = this.Content.Load<Texture2D>("ball");


            ballShape = new CircleShape(ConvertUnits.ToSimUnits(ballTexture.Width) / 2, 1f);

            world = new World(new Vector2(0, 10f));

            float paddleLength = 0.8f;
            //float handOffset = paddleLength * -0.4f;
            float handOffset = paddleLength * 0f;
            //float elbowOffset = paddleLength * 0.4f;
            float elbowOffset = paddleLength * 0.8f;

            // Left
            leftArm = addRectangleObject(paddleLength, 0.2f, worldSimWidth, 0.5f, true);
            leftHandJoint = JointFactory.CreateFixedMouseJoint(world, leftArm, new Vector2(0f, 0f));
            leftHandJoint.LocalAnchorA = new Vector2(handOffset, 0f);
            leftElbowJoint = JointFactory.CreateFixedMouseJoint(world, leftArm, new Vector2(0f, 0f));
            leftElbowJoint.LocalAnchorA = new Vector2(elbowOffset, 0f);

            // Right
            rightArm = addRectangleObject(paddleLength, 0.2f, 0.5f, 0.5f, true);
            rightHandJoint = JointFactory.CreateFixedMouseJoint(world, rightArm, new Vector2(0f, 0f));
            rightHandJoint.LocalAnchorA = new Vector2(handOffset, 0f);
            rightElbowJoint = JointFactory.CreateFixedMouseJoint(world, rightArm, new Vector2(0f, 0f));
            rightElbowJoint.LocalAnchorA = new Vector2(elbowOffset, 0f);
            
            // Add terrain
            float wallWidth = 0.05f;
            // Left wall
            addRectangleObject(wallWidth, worldSimHeight / 3, wallWidth / 2, worldSimHeight / 6, false);
            addRectangleObject(wallWidth, worldSimHeight / 3, wallWidth / 2, 5 * worldSimHeight / 6, false);
            
            // Right wall
            addRectangleObject(wallWidth, worldSimHeight / 3, worldSimWidth - wallWidth / 2, worldSimHeight / 6, false);
            addRectangleObject(wallWidth, worldSimHeight / 3, worldSimWidth - wallWidth / 2, 5 * worldSimHeight / 6, false);

            addRectangleObject(worldSimWidth, wallWidth, worldSimWidth / 2, wallWidth / 2, false);
            addRectangleObject(worldSimWidth, wallWidth, worldSimWidth / 2, worldSimHeight - wallWidth / 2, false);

            // Add net
            //addRectangleObject(0.2f, worldSimHeight * 0.6f, worldSimWidth / 2, worldSimHeight * 1.0f, false);

            //acknowledgeSound = Content.Load<SoundEffect>("communications_start_transmission");
            //affirmativeSound = Content.Load<SoundEffect>("affirmative");
            //bogusSound = Content.Load<SoundEffect>("donotaddressthisunitinthatmanner_clean");
            //goalSound = Content.Load<SoundEffect>("consolewarning");
            //awaitingSound = Content.Load<SoundEffect>("awaiting");

            resetGame();

            //awaitingSound.Play();
        }

        /// <summary>
        /// UnloadContent will be called once per game and is the place to unload
        /// all content.
        /// </summary>
        protected override void UnloadContent()
        {
            // TODO: Unload any non ContentManager content here
        }

        /// <summary>
        /// Allows the game to run logic such as updating the world,
        /// checking for collisions, gathering input, and playing audio.
        /// </summary>
        /// <param name="gameTime">Provides a snapshot of timing values.</param>
        protected override void Update(GameTime gameTime)
        {
            // Allows the game to exit
            if ((Keyboard.GetState(PlayerIndex.One).IsKeyDown(Keys.Escape)) || (GamePad.GetState(PlayerIndex.One).Buttons.Back == ButtonState.Pressed))
                this.Exit();

            if (Keyboard.GetState(PlayerIndex.One).IsKeyDown(Keys.Space))
            {
                if ((leftScore >= targetScore) || (rightScore >= targetScore))
                {
                    resetGame();
                }
                else
                {
                    resetBall();
                }
            }



            var scale = ConvertUnits.ToDisplayUnits(worldSimWidth) / 640f;

            if (leftTracked)
            {
                Vector2 leftHandPosition = new Vector2(ConvertUnits.ToSimUnits(leftHandPoint.X * scale), ConvertUnits.ToSimUnits(leftHandPoint.Y * scale));
                leftHandJoint.WorldAnchorB = leftHandPosition;
                Vector2 leftElbowPosition = new Vector2(ConvertUnits.ToSimUnits(leftElbowPoint.X * scale), ConvertUnits.ToSimUnits(leftElbowPoint.Y * scale));
                leftElbowJoint.WorldAnchorB = leftElbowPosition;
            }

            if (rightTracked)
            {
                Vector2 rightHandPosition = new Vector2(ConvertUnits.ToSimUnits(rightHandPoint.X * scale), ConvertUnits.ToSimUnits(rightHandPoint.Y * scale));
                rightHandJoint.WorldAnchorB = rightHandPosition;
                Vector2 rightElbowPosition = new Vector2(ConvertUnits.ToSimUnits(rightElbowPoint.X * scale), ConvertUnits.ToSimUnits(rightElbowPoint.Y * scale));
                rightElbowJoint.WorldAnchorB = rightElbowPosition;
            }


            if (ballBody != null)
            {
                if (ballBody.Position.X < 0)
                {
                    rightScore += 1;
                    //goalSound.Play();
                    resetBall();
                }
                else if (ballBody.Position.X > worldSimWidth)
                {
                    leftScore += 1;
                    //goalSound.Play();
                    resetBall();
                }

            }



            if ((leftScore >= targetScore) || (rightScore >= targetScore))
            {
                // Someone won
                if (ballBody != null)
                {
                    world.RemoveBody(ballBody);
                    ballBody = null;
                }
            }
            // variable time step but never less then 30 Hz
            world.Step(Math.Min((float)gameTime.ElapsedGameTime.TotalSeconds, (1f / 30f)));

            //l.Update(gameTime);

            TimeSpan timeDiff = DateTime.Now - lastAcknowledgeTime;
            if (((listening) && (timeDiff.TotalSeconds > 5)) || (commandExecuted))
            {
                listening = false;
                commandExecuted = false;

                speechRecognizer.RequestRecognizerUpdate();
                speechRecognizer.UnloadAllGrammars();
                speechRecognizer.LoadGrammar(startGrammar);
            }

            base.Update(gameTime);


        }

        /// <summary>
        /// This is called when the game should draw itself.
        /// </summary>
        /// <param name="gameTime">Provides a snapshot of timing values.</param>
        protected override void Draw(GameTime gameTime)
        {
            GraphicsDevice.Clear(Color.CornflowerBlue);

            spriteBatch.Begin();

            // Draw RGB video
            if (colorVideo != null)
            {
                var scale = ConvertUnits.ToDisplayUnits(worldSimWidth) / 640f;

                spriteBatch.Draw(colorVideo, Vector2.Zero, null, Color.White, 0f, Vector2.Zero, scale, SpriteEffects.None, 0f);
            }

            for (int i = 0; i < bodies.Count; i++)
            {
                Body b = bodies[i];
                Texture2D t = textures[i];
                Vector2 o = origins[i];
                Color c = Color.Black;

                if (b == leftArm)
                {
                    c = Color.White;
                }
                else if (b == rightArm)
                {
                    c = Color.White;
                }
                spriteBatch.Draw(t, ConvertUnits.ToDisplayUnits(b.Position), null, c, b.Rotation, o, 1.0f, SpriteEffects.None, 0f);
            }

            if (ballBody != null)
            {
                spriteBatch.Draw(ballTexture, ConvertUnits.ToDisplayUnits(ballBody.Position), null, Color.White, ballBody.Rotation, ballOrigin, 1.0f, SpriteEffects.None, 0f);
            }

            font = Content.Load<SpriteFont>("batsfont");
            spriteBatch.DrawString(font, leftScore.ToString(), new Vector2(10, 10), Color.Red);
            spriteBatch.DrawString(font, rightScore.ToString(), new Vector2(ConvertUnits.ToDisplayUnits(worldSimWidth) - 80, 10), Color.Blue);

            if (leftScore >= targetScore)
            {
                spriteBatch.DrawString(font, "Red player won!", new Vector2(ConvertUnits.ToDisplayUnits(worldSimWidth / 2) - 300, ConvertUnits.ToDisplayUnits(worldSimHeight / 2)), Color.Red);
            }
            else if (rightScore >= targetScore)
            {
                spriteBatch.DrawString(font, "Blue player won!", new Vector2(ConvertUnits.ToDisplayUnits(worldSimWidth / 2) - 300, ConvertUnits.ToDisplayUnits(worldSimHeight / 2)), Color.Blue);
            }

            spriteBatch.End();

            base.Draw(gameTime);
        }

        void StopKinect(KinectSensor sensor)
        {
            if (sensor == null)
            {
                return;
            }

            if ((sensor.SkeletonStream != null) && (sensor.SkeletonStream.IsEnabled))
            {
                sensor.SkeletonStream.Disable();
            }

            if ((sensor.ColorStream != null) && (sensor.ColorStream.IsEnabled))
            {
                sensor.ColorStream.Disable();
            }

            if ((sensor.DepthStream != null) && (sensor.DepthStream.IsEnabled))
            {
                sensor.DepthStream.Disable();
            }

            // detach event handlers
            sensor.AllFramesReady -= this.kinect_AllFramesReady;

            try
            {
                sensor.Stop();
            }
            catch (Exception e)
            {
                Debug.WriteLine("unknown Exception {0}", e.Message);
            }
        }

        protected override void OnExiting(Object sender, EventArgs args)
        {
            done = true;

            StopKinect(kinect);

            base.OnExiting(sender, args);
        }

    }
}


